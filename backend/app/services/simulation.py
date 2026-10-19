from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.db.postgres.session import engine
from backend.app.schemas.api import SimulationStatus
from backend.app.services.eca import evaluate_observation_context
from backend.app.services.simulation_config import SIMULATION_PATHS, SPECIES_SPEED_CAP_KMH, SimulationPoint

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

    def _step_sync(self, observed_at: datetime | None = None) -> list[dict[str, Any]]:
        candidates = []
        for animal_id, path in SIMULATION_PATHS.items():
            step_index = self._steps[animal_id]
            if step_index >= len(path):
                continue
            current_point = path[step_index]
            previous_point = path[max(step_index - 1, 0)]
            candidates.append({
                "animal_id": animal_id,
                "step_index": step_index,
                "point": current_point,
                "previous_point": previous_point,
            })
        if not candidates:
            return []

        animal_ids = [item["animal_id"] for item in candidates]
        longitudes = [item["point"].longitude for item in candidates]
        latitudes = [item["point"].latitude for item in candidates]
        known_zone_ids = [self._current_zones.get(animal_id) for animal_id in animal_ids]
        fix_at = observed_at or datetime.now(timezone.utc)
        pending_steps = {}
        pending_zones = {}
        emitted: list[dict[str, Any]] = []
        with engine.begin() as conn:
            rows = [dict(row) for row in conn.execute(text("""
                WITH routes AS (
                    SELECT * FROM unnest(CAST(:animal_ids AS varchar[]),
                                         CAST(:longitudes AS double precision[]),
                                         CAST(:latitudes AS double precision[]),
                                         CAST(:known_zone_ids AS varchar[]))
                         AS r(animal_id, longitude, latitude, known_zone_id)
                ), rules AS (
                    SELECT coalesce(jsonb_agg(jsonb_build_object(
                        'rule_id', rule_id, 'rule_name', rule_name, 'event_type', event_type,
                        'condition', condition, 'action', action, 'severity', severity,
                        'enabled', enabled, 'version_no', version_no
                    ) ORDER BY rule_id), '[]'::jsonb) AS active_rules
                    FROM eca_rules WHERE enabled = true
                )
                SELECT a.animal_id, a.animal_code, a.name, a.species, a.device_id, d.battery_level,
                       r.longitude, r.latitude,
                       current_zone.zone_id AS current_zone_id,
                       current_zone.zone_name AS current_zone_name,
                       current_zone.zone_type AS current_zone_type,
                       current_zone.risk_level AS current_zone_risk,
                       coalesce(r.known_zone_id, previous_zone.zone_id) AS previous_zone_id,
                       rules.active_rules
                FROM routes r
                JOIN animals a ON a.animal_id=r.animal_id AND a.device_id IS NOT NULL
                JOIN devices d ON d.device_id=a.device_id
                LEFT JOIN LATERAL (
                    SELECT zone_id, zone_name, zone_type, risk_level FROM zones
                    WHERE ST_Covers(geometry, ST_SetSRID(ST_MakePoint(r.longitude, r.latitude), 4326))
                    ORDER BY CASE risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                             WHEN 'medium' THEN 2 ELSE 3 END, ST_Area(geometry), zone_id
                    LIMIT 1
                ) current_zone ON true
                LEFT JOIN LATERAL (
                    SELECT z.zone_id
                    FROM observations o
                    LEFT JOIN LATERAL (
                        SELECT zone_id FROM zones WHERE ST_Covers(geometry, o.location)
                        ORDER BY CASE risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                                 WHEN 'medium' THEN 2 ELSE 3 END, ST_Area(geometry), zone_id
                        LIMIT 1
                    ) z ON true
                    WHERE r.known_zone_id IS NULL AND o.animal_id=a.animal_id
                    ORDER BY o.observed_at DESC, o.observation_id DESC
                    LIMIT 1
                ) previous_zone ON true
                CROSS JOIN rules
            """), {"animal_ids": animal_ids, "longitudes": longitudes,
                  "latitudes": latitudes, "known_zone_ids": known_zone_ids}).mappings()]
            if not rows:
                return []

            ready = []
            candidate_by_id = {item["animal_id"]: item for item in candidates}
            active_rules_by_event: dict[str, list[dict[str, Any]]] = {}
            for rule in rows[0]["active_rules"] or []:
                active_rules_by_event.setdefault(str(rule["event_type"]), []).append(rule)
            for row in rows:
                candidate = candidate_by_id[row["animal_id"]]
                point = candidate["point"]
                previous_point = candidate["previous_point"]
                ready.append({
                    **candidate,
                    "animal": row,
                    "point": point,
                    "speed": self._speed_for(row["species"], previous_point, point),
                    "observed_at": fix_at,
                    "observation_id": f"OBS-SIM-{uuid4().hex[:18].upper()}",
                    "current_zone_id": str(row["current_zone_id"]) if row["current_zone_id"] else None,
                    "previous_zone_id": str(row["previous_zone_id"]) if row["previous_zone_id"] else None,
                    "current_zone": {
                        "zone_id": row["current_zone_id"], "zone_name": row["current_zone_name"],
                        "zone_type": row["current_zone_type"], "risk_level": row["current_zone_risk"],
                    } if row["current_zone_id"] else None,
                })

            conn.execute(text("""
                WITH fixes AS (
                    SELECT * FROM unnest(CAST(:observation_ids AS varchar[]),
                                         CAST(:animal_ids AS varchar[]),
                                         CAST(:device_ids AS varchar[]),
                                         CAST(:latitudes AS double precision[]),
                                         CAST(:longitudes AS double precision[]),
                                         CAST(:speeds AS double precision[]),
                                         CAST(:observed_ats AS timestamptz[]),
                                         CAST(:previous_zone_ids AS varchar[]),
                                         CAST(:current_zone_ids AS varchar[]),
                                         CAST(:boundary_event_ids AS varchar[]))
                         AS f(observation_id, animal_id, device_id, latitude, longitude, speed,
                              observed_at, previous_zone_id, current_zone_id, boundary_event_id)
                ), inserted AS (
                INSERT INTO observations
                  (observation_id, animal_id, device_id, latitude, longitude, speed, observed_at, location)
                SELECT f.observation_id, f.animal_id, f.device_id, f.latitude, f.longitude, f.speed, f.observed_at,
                       ST_SetSRID(ST_MakePoint(f.longitude, f.latitude), 4326)
                FROM fixes f RETURNING animal_id
                ), updated_devices AS (
                    UPDATE devices d SET last_seen=f.observed_at, updated_at=now()
                    FROM fixes f WHERE d.device_id=f.device_id RETURNING d.device_id
                ), boundary_events AS (
                    INSERT INTO event_outbox (event_id, collection_name, payload)
                    SELECT f.boundary_event_id, 'boundary_events', jsonb_build_object(
                        'event_type', 'boundary_crossing', 'animal_id', f.animal_id,
                        'timestamp', f.observed_at, 'from_zone_id', f.previous_zone_id,
                        'to_zone_id', f.current_zone_id,
                        'location', jsonb_build_object('lat', f.latitude, 'lng', f.longitude),
                        'metadata', jsonb_build_object('speed', f.speed, 'source', 'simulator')
                    )
                    FROM fixes f WHERE f.current_zone_id IS DISTINCT FROM f.previous_zone_id
                    RETURNING event_id
                )
                SELECT (SELECT count(*) FROM inserted),
                       (SELECT count(*) FROM updated_devices),
                       (SELECT count(*) FROM boundary_events)
            """), {
                "observation_ids": [item["observation_id"] for item in ready],
                "animal_ids": [item["animal_id"] for item in ready],
                "device_ids": [item["animal"]["device_id"] for item in ready],
                "latitudes": [item["point"].latitude for item in ready],
                "longitudes": [item["point"].longitude for item in ready],
                "speeds": [item["speed"] for item in ready],
                "observed_ats": [item["observed_at"] for item in ready],
                "previous_zone_ids": [item["previous_zone_id"] for item in ready],
                "current_zone_ids": [item["current_zone_id"] for item in ready],
                "boundary_event_ids": [str(uuid4()) for _ in ready],
            })

            for item in ready:
                animal_id = item["animal_id"]
                animal = item["animal"]
                point = item["point"]
                fix_at = item["observed_at"]
                zone = item["current_zone"]
                current_zone_id = item["current_zone_id"]
                previous_zone_id = item["previous_zone_id"]
                observation = {
                    "observation_id": item["observation_id"], "animal_id": animal["animal_id"],
                    "device_id": animal["device_id"], "latitude": point.latitude,
                    "longitude": point.longitude, "speed": item["speed"], "observed_at": fix_at,
                }
                evaluate_observation_context(
                    conn, animal=animal, observation=observation,
                    current_zone=zone,
                    previous_zone_id=previous_zone_id,
                    active_rules_by_event=active_rules_by_event,
                )
                pending_zones[animal_id] = current_zone_id
                pending_steps[animal_id] = item["step_index"] + 1
                emitted.append({"animal_id": animal_id, "observation": observation, "zone_id": current_zone_id})
        # Update process state only after PostgreSQL has committed every observation.
        self._current_zones.update(pending_zones)
        self._steps.update(pending_steps)
        return emitted

    def _speed_for(self, species: str, previous_point: SimulationPoint, current_point: SimulationPoint) -> float:
        if previous_point == current_point:
            return 0.0
        kmh = (distance_meters(previous_point, current_point) / max(self.interval_seconds, 1)) * 3.6
        cap = SPECIES_SPEED_CAP_KMH.get(species, 24.0)
        return round(min(kmh, cap), 2)

simulator = MovementSimulator()
