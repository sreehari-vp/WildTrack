"""Rebuildable Neo4j projection of PostgreSQL/PostGIS movement history."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from uuid import uuid4

from neo4j import GraphDatabase
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.db.postgres.session import engine

logger = logging.getLogger(__name__)
_sync_lock = threading.Lock()
MAX_TRANSITION_GAP_SECONDS = 6 * 60 * 60
PROJECTION_VERSION = "1"

ZONE_SQL = """
    SELECT DISTINCT ON (v.zone_id) v.zone_id, v.zone_name, v.zone_type,
           v.risk_level, v.version_no, z.zone_id IS NULL AS retired
    FROM zone_versions v LEFT JOIN zones z ON z.zone_id=v.zone_id
    ORDER BY v.zone_id, v.version_no DESC
"""
ANIMAL_SQL = "SELECT animal_id, animal_code, name, species FROM animals ORDER BY animal_id"
FIX_SQL = """
    SELECT o.observation_id, o.animal_id, a.species, o.observed_at,
           z.zone_id
    FROM observations o JOIN animals a ON a.animal_id=o.animal_id
    LEFT JOIN LATERAL (
        SELECT v.zone_id FROM zone_versions v
        WHERE v.valid_from <= o.observed_at
          AND (v.valid_to IS NULL OR o.observed_at < v.valid_to)
          AND ST_Covers(v.geometry, o.location)
        ORDER BY CASE v.risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                 WHEN 'medium' THEN 2 ELSE 3 END,
                 ST_Area(v.geometry), v.zone_id LIMIT 1
    ) z ON true
    ORDER BY o.animal_id, o.observed_at, o.observation_id
"""
SIGNATURE_SQL = """
    SELECT (SELECT count(*) FROM observations) AS observation_count,
           (SELECT max(observed_at) FROM observations) AS latest_observation,
           (SELECT count(*) FROM zone_versions) AS zone_version_count,
           (SELECT max(valid_to) FROM zone_versions) AS latest_zone_close,
           (SELECT count(*) FROM animals) AS animal_count,
           (SELECT max(updated_at) FROM animals) AS latest_animal_update
"""


def configured() -> bool:
    return get_settings().neo4j_configured


@lru_cache(maxsize=1)
def get_driver():
    settings = get_settings()
    if not settings.neo4j_configured:
        raise RuntimeError("Neo4j Aura is not configured")
    if not settings.neo4j_uri.startswith("neo4j+s://"):
        raise ValueError("Aura URI must use neo4j+s://")
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
        connection_timeout=8,
        max_connection_pool_size=10,
    )


def close_driver() -> None:
    if get_driver.cache_info().currsize:
        get_driver().close()
        get_driver.cache_clear()


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Movement timestamps must include a timezone")
    return value.astimezone(timezone.utc).isoformat()


def _signature(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps({"projection_version": PROJECTION_VERSION, **dict(data)}, default=str, sort_keys=True).encode()).hexdigest()


def current_source_signature() -> str:
    with engine.connect() as conn:
        return _signature(conn.execute(text(SIGNATURE_SQL)).mappings().one())


def build_daily_corridors(fixes: Iterable[Mapping[str, Any]]) -> tuple[list[dict], list[dict], list[dict]]:
    """Ignore outside-zone fixes; connect only successive zone visits <=6h apart."""
    last_visit: dict[str, tuple[str, datetime]] = {}
    animal_days: dict[tuple[str, str, str, str], dict] = {}
    for fix in fixes:
        zone_id = fix.get("zone_id")
        if not zone_id:
            continue
        animal_id = str(fix["animal_id"])
        observed_at = fix["observed_at"]
        previous = last_visit.get(animal_id)
        if previous and previous[0] != zone_id:
            elapsed = (observed_at - previous[1]).total_seconds()
            if 0 <= elapsed <= MAX_TRANSITION_GAP_SECONDS:
                day = observed_at.astimezone(timezone.utc).date().isoformat()
                key = (day, previous[0], str(zone_id), animal_id)
                item = animal_days.setdefault(key, {
                    "date": day, "from_zone_id": previous[0], "to_zone_id": str(zone_id),
                    "animal_id": animal_id, "species": fix["species"],
                    "count": 0, "first_at": _utc_iso(observed_at), "last_at": _utc_iso(observed_at),
                })
                item["count"] += 1
                item["last_at"] = _utc_iso(observed_at)
        last_visit[animal_id] = (str(zone_id), observed_at)

    day_groups: dict[tuple[str, str, str], dict] = {}
    corridors: dict[tuple[str, str], dict] = {}
    for item in animal_days.values():
        day_key = (item["date"], item["from_zone_id"], item["to_zone_id"])
        day = day_groups.setdefault(day_key, {
            "date": item["date"], "from_zone_id": item["from_zone_id"],
            "to_zone_id": item["to_zone_id"], "crossings": 0, "animal_ids": set(),
            "last_at": item["last_at"],
        })
        day["crossings"] += item["count"]
        day["animal_ids"].add(item["animal_id"])
        day["last_at"] = max(day["last_at"], item["last_at"])
        pair_key = (item["from_zone_id"], item["to_zone_id"])
        corridor = corridors.setdefault(pair_key, {
            "from_zone_id": item["from_zone_id"], "to_zone_id": item["to_zone_id"],
            "crossings": 0, "animal_ids": set(), "last_at": item["last_at"],
        })
        corridor["crossings"] += item["count"]
        corridor["animal_ids"].add(item["animal_id"])
        corridor["last_at"] = max(corridor["last_at"], item["last_at"])

    days = [{**item, "animals": len(item["animal_ids"])} for item in day_groups.values()]
    for item in days:
        del item["animal_ids"]
    edges = [{**item, "animals": len(item["animal_ids"])} for item in corridors.values()]
    for item in edges:
        del item["animal_ids"]
    return (
        sorted(days, key=lambda row: (row["date"], row["from_zone_id"], row["to_zone_id"])),
        sorted(animal_days.values(), key=lambda row: (row["date"], row["from_zone_id"], row["to_zone_id"], row["animal_id"])),
        sorted(edges, key=lambda row: (row["from_zone_id"], row["to_zone_id"])),
    )


def read_source_projection() -> dict:
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        signature_data = dict(conn.execute(text(SIGNATURE_SQL)).mappings().one())
        zones = [dict(row) for row in conn.execute(text(ZONE_SQL)).mappings()]
        animals = [dict(row) for row in conn.execute(text(ANIMAL_SQL)).mappings()]
        stream = conn.execution_options(stream_results=True).execute(text(FIX_SQL)).mappings()
        days, animal_days, edges = build_daily_corridors(stream)
    signature = _signature(signature_data)
    return {"signature": signature, "zones": zones, "animals": animals,
            "days": days, "animal_days": animal_days, "edges": edges,
            "observation_count": signature_data["observation_count"]}


def _run(session, query: str, **params):
    session.run(query, **params).consume()


def _chunks(items: list[dict], size: int = 500):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _cleanup_inactive(session, active_generation: str | None) -> None:
    while True:
        summary = session.run("""
            MATCH (n) WHERE (n:WildTrackZone OR n:WildTrackAnimal OR n:WildTrackCorridorDay)
              AND ($active IS NULL OR n.generation <> $active)
            WITH n LIMIT 500 DETACH DELETE n
        """, active=active_generation).consume()
        if not summary.counters.nodes_deleted:
            break


def _acquire_global_sync_lock():
    guard = engine.connect()
    try:
        acquired = guard.execute(text("SELECT pg_try_advisory_lock(hashtext('wildtrack-neo4j-sync'))")).scalar_one()
        guard.commit()
        if not acquired:
            raise RuntimeError("A network synchronization is already running")
        return guard
    except Exception:
        guard.close()
        raise


def _release_global_sync_lock(guard) -> None:
    try:
        guard.execute(text("SELECT pg_advisory_unlock(hashtext('wildtrack-neo4j-sync'))"))
        guard.commit()
    finally:
        guard.close()


def sync_projection(*, force: bool = False) -> dict:
    if not configured():
        raise RuntimeError("Neo4j Aura is not configured")
    if not _sync_lock.acquire(blocking=False):
        raise RuntimeError("A network synchronization is already running")
    guard = None
    try:
        guard = _acquire_global_sync_lock()
        settings = get_settings()
        driver = get_driver()
        driver.verify_connectivity()
        with driver.session(database=settings.neo4j_database) as session:
            meta = session.run("""
                MATCH (p:WildTrackProjection {name:'wildtrack'})
                RETURN p.active_generation AS generation, p.source_signature AS signature,
                       p.synced_at AS synced_at
            """).single()
            if meta and meta["signature"] == current_source_signature() and not force:
                _cleanup_inactive(session, meta["generation"])
                return {"changed": False, "synced_at": meta["synced_at"], "generation": meta["generation"]}
            source = read_source_projection()
            active = meta["generation"] if meta else None
            _cleanup_inactive(session, active)
            generation = str(uuid4())
            for label in ("WildTrackZone", "WildTrackAnimal", "WildTrackCorridorDay"):
                _run(session, f"CREATE CONSTRAINT {label.lower()}_key IF NOT EXISTS FOR (n:{label}) REQUIRE n.key IS UNIQUE")
            zones = [{**z, "key": f"{generation}|{z['zone_id']}", "generation": generation} for z in source["zones"]]
            animals = [{**a, "key": f"{generation}|{a['animal_id']}", "generation": generation} for a in source["animals"]]
            days = [{**d, "key": f"{generation}|{d['date']}|{d['from_zone_id']}|{d['to_zone_id']}",
                     "generation": generation, "from_key": f"{generation}|{d['from_zone_id']}",
                     "to_key": f"{generation}|{d['to_zone_id']}"} for d in source["days"]]
            uses = [{**u, "day_key": f"{generation}|{u['date']}|{u['from_zone_id']}|{u['to_zone_id']}",
                     "animal_key": f"{generation}|{u['animal_id']}"} for u in source["animal_days"]]
            edges = [{**e, "from_key": f"{generation}|{e['from_zone_id']}",
                      "to_key": f"{generation}|{e['to_zone_id']}"} for e in source["edges"]]
            for batch in _chunks(zones):
                _run(session, """
                    UNWIND $rows AS row MERGE (n:WildTrackZone {key:row.key})
                    SET n.generation=row.generation, n.zone_id=row.zone_id,
                        n.name=row.zone_name, n.zone_type=row.zone_type,
                        n.risk_level=row.risk_level, n.retired=row.retired
                """, rows=batch)
            for batch in _chunks(animals):
                _run(session, """
                    UNWIND $rows AS row MERGE (n:WildTrackAnimal {key:row.key})
                    SET n.generation=row.generation, n.animal_id=row.animal_id,
                        n.code=row.animal_code, n.name=row.name, n.species=row.species
                """, rows=batch)
            for batch in _chunks(days):
                _run(session, """
                    UNWIND $rows AS row
                    MATCH (source:WildTrackZone {key:row.from_key})
                    MATCH (target:WildTrackZone {key:row.to_key})
                    MERGE (day:WildTrackCorridorDay {key:row.key})
                    SET day.generation=row.generation, day.date=row.date,
                        day.from_zone_id=row.from_zone_id, day.to_zone_id=row.to_zone_id,
                        day.crossings=row.crossings, day.animals=row.animals, day.last_at=row.last_at
                    MERGE (day)-[:WILDTRACK_FROM]->(source)
                    MERGE (day)-[:WILDTRACK_TO]->(target)
                """, rows=batch)
            for batch in _chunks(uses):
                _run(session, """
                    UNWIND $rows AS row
                    MATCH (animal:WildTrackAnimal {key:row.animal_key})
                    MATCH (day:WildTrackCorridorDay {key:row.day_key})
                    MERGE (animal)-[used:WILDTRACK_USED]->(day)
                    SET used.count=row.count, used.first_at=row.first_at, used.last_at=row.last_at
                """, rows=batch)
            for batch in _chunks(edges):
                _run(session, """
                    UNWIND $rows AS row
                    MATCH (source:WildTrackZone {key:row.from_key})
                    MATCH (target:WildTrackZone {key:row.to_key})
                    MERGE (source)-[edge:WILDTRACK_CORRIDOR]->(target)
                    SET edge.crossings=row.crossings, edge.animals=row.animals, edge.last_at=row.last_at
                """, rows=batch)
            synced_at = datetime.now(timezone.utc).isoformat()
            _run(session, """
                MERGE (p:WildTrackProjection {name:'wildtrack'})
                SET p.active_generation=$generation, p.source_signature=$signature,
                    p.synced_at=$synced_at, p.zones=$zones, p.corridors=$corridors,
                    p.observations=$observations
            """, generation=generation, signature=source["signature"], synced_at=synced_at,
                 zones=len(zones), corridors=len(edges), observations=source["observation_count"])
            try:
                _cleanup_inactive(session, generation)
            except Exception as exc:
                logger.warning("Inactive graph cleanup delayed (%s)", type(exc).__name__)
            return {"changed": True, "synced_at": synced_at, "generation": generation,
                    "zones": len(zones), "corridors": len(edges), "daily_corridors": len(days)}
    finally:
        try:
            if guard is not None:
                _release_global_sync_lock(guard)
        finally:
            _sync_lock.release()


def projection_status() -> dict:
    if not configured():
        return {"configured": False, "ready": False, "synced_at": None}
    settings = get_settings()
    with get_driver().session(database=settings.neo4j_database) as session:
        row = session.run("""
            MATCH (p:WildTrackProjection {name:'wildtrack'})
            RETURN p.active_generation AS generation, p.synced_at AS synced_at,
                   p.zones AS zones, p.corridors AS corridors, p.observations AS observations,
                   p.source_signature AS source_signature
        """).single()
        stale = bool(row and row["source_signature"] != current_source_signature())
        return {"configured": True, "ready": bool(row and row["generation"]),
                "synced_at": row["synced_at"] if row else None,
                "zones": row["zones"] if row else 0,
                "corridors": row["corridors"] if row else 0,
                "observations": row["observations"] if row else 0,
                "stale": stale, "syncing": _sync_lock.locked()}


def network_snapshot(*, species: str | None = None, start_date: str | None = None,
                     end_date: str | None = None) -> dict:
    status = projection_status()
    if not status["ready"]:
        return {**status, "zones": [], "corridors": [], "species": []}
    settings = get_settings()
    with get_driver().session(database=settings.neo4j_database) as session:
        meta = session.run("MATCH (p:WildTrackProjection {name:'wildtrack'}) RETURN p.active_generation AS generation").single()
        generation = meta["generation"]
        zones = [dict(row) for row in session.run("""
            MATCH (z:WildTrackZone {generation:$generation})
            RETURN z.zone_id AS zone_id, z.name AS name, z.zone_type AS zone_type,
                   z.risk_level AS risk_level, z.retired AS retired ORDER BY z.name
        """, generation=generation)]
        species_list = [row["species"] for row in session.run("""
            MATCH (a:WildTrackAnimal {generation:$generation})
            RETURN DISTINCT a.species AS species ORDER BY species
        """, generation=generation) if row["species"]]
        corridors = [dict(row) for row in session.run("""
            MATCH (a:WildTrackAnimal {generation:$generation})-[used:WILDTRACK_USED]->
                  (day:WildTrackCorridorDay {generation:$generation})-[:WILDTRACK_FROM]->(source:WildTrackZone)
            MATCH (day)-[:WILDTRACK_TO]->(target:WildTrackZone)
            WHERE ($species IS NULL OR a.species=$species)
              AND ($start_date IS NULL OR day.date >= $start_date)
              AND ($end_date IS NULL OR day.date <= $end_date)
            RETURN source.zone_id AS from_zone_id, target.zone_id AS to_zone_id,
                   sum(used.count) AS crossings, count(DISTINCT a.animal_id) AS animals,
                   max(used.last_at) AS last_at
            ORDER BY crossings DESC, from_zone_id, to_zone_id
        """, generation=generation, species=species,
             start_date=start_date, end_date=end_date)]
    return {**status, "zones": zones, "corridors": corridors, "species": species_list,
            "filters": {"species": species, "start_date": start_date, "end_date": end_date}}


def corridor_detail(from_zone_id: str, to_zone_id: str, *, species: str | None = None,
                    start_date: str | None = None, end_date: str | None = None) -> dict:
    status = projection_status()
    if not status["ready"]:
        return {"animals": [], "crossings": 0, "alerts": []}
    settings = get_settings()
    with get_driver().session(database=settings.neo4j_database) as session:
        row = session.run("MATCH (p:WildTrackProjection {name:'wildtrack'}) RETURN p.active_generation AS generation").single()
        generation = row["generation"]
        animals = [dict(record) for record in session.run("""
            MATCH (a:WildTrackAnimal {generation:$generation})-[used:WILDTRACK_USED]->
                  (day:WildTrackCorridorDay {generation:$generation,
                       from_zone_id:$from_id, to_zone_id:$to_id})
            WHERE ($species IS NULL OR a.species=$species)
              AND ($start_date IS NULL OR day.date >= $start_date)
              AND ($end_date IS NULL OR day.date <= $end_date)
            RETURN a.animal_id AS animal_id, a.code AS animal_code, a.name AS name,
                   a.species AS species, sum(used.count) AS crossings,
                   max(used.last_at) AS last_at
            ORDER BY crossings DESC, animal_code
        """, generation=generation, from_id=from_zone_id, to_id=to_zone_id,
             species=species, start_date=start_date, end_date=end_date)]
    alerts = _related_alerts([a["animal_id"] for a in animals], [from_zone_id, to_zone_id], start_date, end_date)
    return {"from_zone_id": from_zone_id, "to_zone_id": to_zone_id, "animals": animals,
            "crossings": sum(a["crossings"] for a in animals), "alerts": alerts}


def _related_alerts(animal_ids: list[str], zone_ids: list[str], start_date: str | None,
                    end_date: str | None) -> list[dict]:
    if not animal_ids:
        return []
    params: dict[str, Any] = {"animal_ids": animal_ids, "zone_ids": zone_ids}
    clauses = ["animal_id=ANY(:animal_ids)", "zone_id=ANY(:zone_ids)"]
    if start_date:
        clauses.append("created_at >= CAST(:start_date AS date)")
        params["start_date"] = start_date
    if end_date:
        clauses.append("created_at < CAST(:end_date AS date) + interval '1 day'")
        params["end_date"] = end_date
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(text(f"""
            SELECT alert_id, animal_id, zone_id, severity, message, created_at
            FROM alerts WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC LIMIT 20
        """), params).mappings()]


def habitat_impact(zone_id: str, max_hops: int = 3) -> dict:
    status = projection_status()
    if not status["ready"]:
        return {"origin_zone_id": zone_id, "reachable_zones": [], "animals": [], "alerts": []}
    settings = get_settings()
    with get_driver().session(database=settings.neo4j_database) as session:
        meta = session.run("MATCH (p:WildTrackProjection {name:'wildtrack'}) RETURN p.active_generation AS generation").single()
        generation = meta["generation"]
        source_key = f"{generation}|{zone_id}"
        if not session.run("MATCH (z:WildTrackZone {key:$key}) RETURN z.zone_id AS id", key=source_key).single():
            raise KeyError(zone_id)
        paths = [dict(row) for row in session.run("""
            MATCH path=(source:WildTrackZone {key:$key})-[:WILDTRACK_CORRIDOR*1..3]-(target:WildTrackZone)
            WHERE length(path) <= $max_hops
              AND all(n IN nodes(path) WHERE single(m IN nodes(path) WHERE m=n))
            WITH target, path ORDER BY length(path)
            WITH target, head(collect(path)) AS shortest
            RETURN target.zone_id AS zone_id, length(shortest) AS hops,
                   [n IN nodes(shortest) | n.zone_id] AS path
            ORDER BY hops, zone_id
        """, key=source_key, max_hops=max_hops)]
        corridors = [dict(row) for row in session.run("""
            MATCH path=(source:WildTrackZone {key:$key})-[:WILDTRACK_CORRIDOR*1..3]-(target:WildTrackZone)
            WHERE length(path) <= $max_hops
              AND all(n IN nodes(path) WHERE single(m IN nodes(path) WHERE m=n))
            UNWIND relationships(path) AS corridor
            WITH corridor, min(length(path)) AS hops
            RETURN startNode(corridor).zone_id AS from_zone_id,
                   endNode(corridor).zone_id AS to_zone_id,
                   corridor.crossings AS crossings, corridor.animals AS animals,
                   corridor.last_at AS last_at, hops
            ORDER BY hops, crossings DESC, from_zone_id, to_zone_id
        """, key=source_key, max_hops=max_hops)]
        corridor_pairs = [{"from_zone_id": edge["from_zone_id"],
                           "to_zone_id": edge["to_zone_id"]} for edge in corridors]
        animals = [dict(row) for row in session.run("""
            MATCH (a:WildTrackAnimal {generation:$generation})-[used:WILDTRACK_USED]->
                  (day:WildTrackCorridorDay {generation:$generation})
            WHERE any(pair IN $corridor_pairs
                      WHERE day.from_zone_id=pair.from_zone_id
                        AND day.to_zone_id=pair.to_zone_id)
            RETURN a.animal_id AS animal_id, a.code AS animal_code,
                   a.name AS name, a.species AS species,
                   sum(used.count) AS crossings
            ORDER BY crossings DESC, animal_code
        """, generation=generation, corridor_pairs=corridor_pairs)]
    zone_ids = [zone_id, *(path["zone_id"] for path in paths)]
    alerts = _related_alerts([a["animal_id"] for a in animals], zone_ids, None, None)
    return {"origin_zone_id": zone_id, "reachable_zones": paths,
            "corridors": corridors, "animals": animals, "alerts": alerts,
            "basis": f"Observed corridors within {max_hops} connection{'s' if max_hops != 1 else ''}; animals used the listed corridors. Historical reachability, not a prediction."}


class NetworkSyncWorker:
    def __init__(self):
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if configured() and (self._task is None or self._task.done()):
            self._task = asyncio.create_task(self._run(), name="wildtrack-neo4j-sync")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        close_driver()

    async def _run(self) -> None:
        interval = max(60, get_settings().neo4j_sync_interval_seconds)
        while True:
            batch = None
            try:
                batch = asyncio.create_task(asyncio.to_thread(sync_projection))
                await asyncio.shield(batch)
            except asyncio.CancelledError:
                if batch is not None:
                    await batch
                raise
            except Exception as exc:
                logger.warning("Neo4j network sync delayed (%s)", type(exc).__name__)
            await asyncio.sleep(interval)


network_sync_worker = NetworkSyncWorker()
