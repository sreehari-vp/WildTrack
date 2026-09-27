from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Any

from pymongo.database import Database
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.db.mongodb.client import ensure_event_indexes, find_forbidden_core_collections, get_mongo_client, get_mongo_database
from backend.app.db.postgres.session import engine
from backend.app.schemas.api import SimulationStatus
from backend.app.services.animals import update_device_seen
from backend.app.services.observations import create_observation
from backend.app.services.simulation_config import SIMULATION_PATHS, SPECIES_SPEED_CAP_KMH, SimulationPoint
from backend.app.services.spatial import zone_containing_point


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

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> SimulationStatus:
        return SimulationStatus(
            running=self.running,
            interval_seconds=self.interval_seconds,
            task_active=self._task is not None and not self._task.done(),
            animals={
                animal_id: {"current_step": step, "current_zone": self._current_zones.get(animal_id)}
                for animal_id, step in self._steps.items()
            },
        )

    async def start(self) -> bool:
        async with self._lock:
            if self.running:
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

    async def _run(self) -> None:
        while True:
            await self.step_once()
            await asyncio.sleep(self.interval_seconds)

    async def step_once(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._step_sync)

    def _load_animal_meta(self) -> dict[str, dict[str, Any]]:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT animal_id, animal_code, species, device_id
                    FROM animals
                    WHERE animal_id = ANY(:animal_ids) OR animal_code = ANY(:animal_ids)
                    """
                ),
                {"animal_ids": list(SIMULATION_PATHS.keys())},
            ).mappings()
            return {row["animal_id"]: dict(row) for row in rows}

    def _step_sync(self) -> list[dict[str, Any]]:
        mongo_client = get_mongo_client()
        mongo_db = get_mongo_database(mongo_client)
        forbidden = find_forbidden_core_collections(mongo_db)
        if forbidden:
            mongo_client.close()
            raise RuntimeError(f"MongoDB contains forbidden core collections: {', '.join(forbidden)}")
        ensure_event_indexes(mongo_db)
        emitted: list[dict[str, Any]] = []
        try:
            meta = self._load_animal_meta()
            with engine.begin() as conn:
                for animal_id, path in SIMULATION_PATHS.items():
                    animal = meta.get(animal_id)
                    if not animal or not animal.get("device_id"):
                        continue
                    step_index = self._steps[animal_id] % len(path)
                    current_point = path[step_index]
                    previous_point = path[(step_index - 1) % len(path)]
                    speed = self._speed_for(animal["species"], previous_point, current_point)
                    observed_at = datetime.now(timezone.utc)
                    observation = create_observation(
                        conn,
                        animal_id=animal["animal_id"],
                        device_id=animal["device_id"],
                        latitude=current_point.latitude,
                        longitude=current_point.longitude,
                        speed=speed,
                        observed_at=observed_at,
                    )
                    update_device_seen(conn, animal["device_id"], observed_at)
                    zones = zone_containing_point(conn, current_point.longitude, current_point.latitude)
                    current_zone_id = str(zones[0]["zone_id"]) if zones else None
                    previous_zone_id = self._current_zones.get(animal_id)
                    if previous_zone_id is None and step_index == 0:
                        previous_zone_id = self._latest_zone_before_simulation(conn, animal_id)
                    if current_zone_id != previous_zone_id:
                        self._record_boundary_event(
                            mongo_db,
                            animal_id=animal_id,
                            timestamp=observed_at,
                            from_zone_id=previous_zone_id,
                            to_zone_id=current_zone_id,
                            latitude=current_point.latitude,
                            longitude=current_point.longitude,
                            speed=speed,
                        )
                    self._current_zones[animal_id] = current_zone_id
                    self._steps[animal_id] = (step_index + 1) % len(path)
                    emitted.append({"animal_id": animal_id, "observation": observation, "zone_id": current_zone_id})
        finally:
            mongo_client.close()
        return emitted

    def _latest_zone_before_simulation(self, conn: Any, animal_id: str) -> str | None:
        row = conn.execute(
            text(
                """
                SELECT z.zone_id
                FROM observations o
                LEFT JOIN zones z ON ST_Contains(z.geometry, o.location)
                WHERE o.animal_id = :animal_id
                ORDER BY o.observed_at DESC
                LIMIT 1
                """
            ),
            {"animal_id": animal_id},
        ).mappings().first()
        return str(row["zone_id"]) if row and row["zone_id"] else None

    def _speed_for(self, species: str, previous_point: SimulationPoint, current_point: SimulationPoint) -> float:
        if previous_point == current_point:
            return 0.0
        kmh = (distance_meters(previous_point, current_point) / max(self.interval_seconds, 1)) * 3.6
        cap = SPECIES_SPEED_CAP_KMH.get(species, 24.0)
        return round(min(kmh, cap), 2)

    def _record_boundary_event(
        self,
        db: Database,
        animal_id: str,
        timestamp: datetime,
        from_zone_id: str | None,
        to_zone_id: str | None,
        latitude: float,
        longitude: float,
        speed: float,
    ) -> None:
        db.boundary_events.insert_one(
            {
                "event_type": "boundary_crossing",
                "animal_id": animal_id,
                "timestamp": timestamp,
                "from_zone_id": from_zone_id,
                "to_zone_id": to_zone_id,
                "location": {"lat": latitude, "lng": longitude},
                "metadata": {"speed": speed, "source": "phase_3_simulator"},
            }
        )


simulator = MovementSimulator()
