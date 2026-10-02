from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Any

from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.db.postgres.session import engine
from backend.app.schemas.api import SimulationStatus
from backend.app.services.animals import update_device_seen
from backend.app.services.eca import evaluate_observation_context
from backend.app.services.observations import create_observation
from backend.app.services.outbox import enqueue_event
from backend.app.services.simulation_config import SIMULATION_PATHS, SPECIES_SPEED_CAP_KMH, SimulationPoint
from backend.app.services.spatial import zone_containing_point

logger = logging.getLogger(__name__)


def distance_meters(a: SimulationPoint, b: SimulationPoint) -> float:
    earth_radius = 6_371_000
    lat1, lon1 = radians(a.latitude), radians(a.longitude)
    lat2, lon2 = radians(b.latitude), radians(b.longitude)
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    h = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
    return 2 * earth_radius * asin(sqrt(h))


class MovementSimulator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.interval_seconds = float(self.settings.simulation_interval_seconds)
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._steps = {animal_id: 0 for animal_id in SIMULATION_PATHS}
        self._current_zones: dict[str, str | None] = {animal_id: None for animal_id in SIMULATION_PATHS}
        self._restored = False

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def finished(self) -> bool:
        return all(self._steps[animal_id] >= len(path) for animal_id, path in SIMULATION_PATHS.items())

    def restore_progress(self) -> None:
        """Resume one-way journeys at the next waypoint after a backend restart."""
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT DISTINCT ON (animal_id) animal_id, longitude, latitude
                FROM observations
                WHERE animal_id = ANY(:animal_ids) AND observation_id LIKE 'OBS-SIM-%'
                ORDER BY animal_id, observed_at DESC, observation_id DESC
            """), {"animal_ids": list(SIMULATION_PATHS)}).mappings()
            for row in rows:
                path = SIMULATION_PATHS[row["animal_id"]]
                observed = SimulationPoint(float(row["longitude"]), float(row["latitude"]))
                closest = min(range(len(path)), key=lambda index: distance_meters(observed, path[index]))
                if distance_meters(observed, path[closest]) <= 80:
                    self._steps[row["animal_id"]] = closest + 1
        self._restored = True

    def status(self) -> SimulationStatus:
        return SimulationStatus(
            running=self.running,
            interval_seconds=self.interval_seconds,
            task_active=self._task is not None and not self._task.done(),
            finished=self.finished,
            completed_routes=sum(self._steps[animal_id] >= len(path) for animal_id, path in SIMULATION_PATHS.items()),
            total_routes=len(SIMULATION_PATHS),
            animals={
                animal_id: {"current_step": step, "current_zone": self._current_zones.get(animal_id)}
                for animal_id, step in self._steps.items()
            },
        )

    async def start(self) -> bool:
        async with self._lock:
            if self.running:
                return False
            if not self._restored:
                await asyncio.to_thread(self.restore_progress)
            if self.finished:
                return False
            self._task = asyncio.create_task(self._run(), name="wildtrack-gps-simulator")
            return True

    async def stop(self) -> bool:
        async with self._lock:
            if not self.running:
                return False
            assert self._task is not None
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            return True

    async def reset(self) -> None:
        if self.running:
            await self.stop()
        self._steps = {animal_id: 0 for animal_id in SIMULATION_PATHS}
        self._current_zones = {animal_id: None for animal_id in SIMULATION_PATHS}
        self._restored = True

    async def _run(self) -> None:
        while not self.finished:
            tick_started = asyncio.get_running_loop().time()
            try:
                await self.step_once()
            except Exception as exc:
                logger.error("Simulation tick failed (%s); retrying next interval", type(exc).__name__)
            if not self.finished:
                elapsed = asyncio.get_running_loop().time() - tick_started
                await asyncio.sleep(max(0, self.interval_seconds - elapsed))

    async def step_once(self, observed_at: datetime | None = None) -> list[dict[str, Any]]:
        if not self._restored:
            await asyncio.to_thread(self.restore_progress)
        worker = asyncio.create_task(asyncio.to_thread(self._step_sync, observed_at))
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            # A thread cannot be cancelled: finish its transaction before reporting stopped.
            await worker
            raise

    def _load_animal_meta(self) -> dict[str, dict[str, Any]]:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT a.animal_id, a.animal_code, a.name, a.species, a.device_id, d.battery_level
                    FROM animals a
                    LEFT JOIN devices d ON d.device_id = a.device_id
                    WHERE a.animal_id = ANY(:animal_ids) OR a.animal_code = ANY(:animal_ids)
                    """
                ),
                {"animal_ids": list(SIMULATION_PATHS.keys())},
            ).mappings()
            return {row["animal_id"]: dict(row) for row in rows}

    def _step_sync(self, observed_at: datetime | None = None) -> list[dict[str, Any]]:
        emitted: list[dict[str, Any]] = []
        pending_steps = {}
        pending_zones = {}
        meta = self._load_animal_meta()
        with engine.begin() as conn:
                for animal_id, path in SIMULATION_PATHS.items():
                    animal = meta.get(animal_id)
                    if not animal or not animal.get("device_id"):
                        continue
                    step_index = self._steps[animal_id]
                    if step_index >= len(path):
                        continue
                    current_point = path[step_index]
                    previous_point = path[max(step_index - 1, 0)]
                    speed = self._speed_for(animal["species"], previous_point, current_point)
                    fix_at = observed_at or datetime.now(timezone.utc)
                    previous_zone_id = self._current_zones.get(animal_id)
                    if previous_zone_id is None:
                        previous_zone_id = self._latest_zone_before_simulation(conn, animal_id, fix_at)
                    observation = create_observation(
                        conn,
                        animal_id=animal["animal_id"],
                        device_id=animal["device_id"],
                        latitude=current_point.latitude,
                        longitude=current_point.longitude,
                        speed=speed,
                        observed_at=fix_at,
                    )
                    update_device_seen(conn, animal["device_id"], fix_at)
                    zones = zone_containing_point(conn, current_point.longitude, current_point.latitude)
                    current_zone_id = str(zones[0]["zone_id"]) if zones else None
                    if current_zone_id != previous_zone_id:
                        enqueue_event(conn, "boundary_events", {
                            "event_type": "boundary_crossing", "animal_id": animal_id,
                            "timestamp": fix_at, "from_zone_id": previous_zone_id,
                            "to_zone_id": current_zone_id,
                            "location": {"lat": current_point.latitude, "lng": current_point.longitude},
                            "metadata": {"speed": speed, "source": "simulator"},
                        })
                    evaluate_observation_context(
                        conn,
                        animal=animal,
                        observation=observation,
                        current_zone=dict(zones[0]) if zones else None,
                        previous_zone_id=previous_zone_id,
                    )
                    pending_zones[animal_id] = current_zone_id
                    pending_steps[animal_id] = step_index + 1
                    emitted.append({"animal_id": animal_id, "observation": observation, "zone_id": current_zone_id})
        # Update process state only after PostgreSQL has committed every observation.
        self._current_zones.update(pending_zones)
        self._steps.update(pending_steps)
        return emitted

    def _latest_zone_before_simulation(self, conn: Any, animal_id: str, observed_at: datetime) -> str | None:
        row = conn.execute(
            text(
                """
                SELECT z.zone_id
                FROM observations o
                LEFT JOIN LATERAL (
                    SELECT * FROM zones WHERE ST_Covers(geometry, o.location)
                    ORDER BY CASE risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                             ST_Area(geometry), zone_id LIMIT 1
                ) z ON true
                WHERE o.animal_id = :animal_id
                  AND o.observed_at >= :since
                  AND o.observed_at < :observed_at
                ORDER BY o.observed_at DESC, o.observation_id DESC
                LIMIT 1
                """
            ),
            {"animal_id": animal_id, "since": observed_at - timedelta(hours=6),
             "observed_at": observed_at},
        ).mappings().first()
        return str(row["zone_id"]) if row and row["zone_id"] else None

    def _speed_for(self, species: str, previous_point: SimulationPoint, current_point: SimulationPoint) -> float:
        if previous_point == current_point:
            return 0.0
        kmh = (distance_meters(previous_point, current_point) / max(self.interval_seconds, 1)) * 3.6
        cap = SPECIES_SPEED_CAP_KMH.get(species, 24.0)
        return round(min(kmh, cap), 2)

simulator = MovementSimulator()
