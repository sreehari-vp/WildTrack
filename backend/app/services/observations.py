from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection


def zone_summary(zone: dict[str, object]) -> dict[str, object]:
    return {
        "zone_id": zone["zone_id"],
        "name": zone["zone_name"],
        "zone_type": zone["zone_type"],
        "risk_level": zone["risk_level"],
    }


def _zone_from_row(row: dict[str, object]) -> dict[str, object] | None:
    if not row.get("zone_id"):
        return None
    return {
        "zone_id": row["zone_id"],
        "name": row["zone_name"],
        "zone_type": row["zone_type"],
        "risk_level": row["risk_level"],
    }


def observation_row_to_dict(row: dict[str, object]) -> dict[str, object]:
    return {
        "observation_id": row["observation_id"],
        "animal_id": row["animal_id"],
        "device_id": row["device_id"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "speed": float(row["speed"]),
        "observed_at": row["observed_at"],
    }


def list_observations(
    conn: Connection,
    animal_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 200,
    descending: bool = True,
) -> list[dict[str, object]]:
    clauses = []
    params: dict[str, object] = {"limit": min(limit, 1000)}
    if animal_id:
        clauses.append("animal_id = :animal_id")
        params["animal_id"] = animal_id
    if start_time:
        clauses.append("observed_at >= :start_time")
        params["start_time"] = start_time
    if end_time:
        clauses.append("observed_at <= :end_time")
        params["end_time"] = end_time
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order = "DESC" if descending else "ASC"
    rows = conn.execute(
        text(
            f"""
            SELECT observation_id, animal_id, device_id, latitude, longitude, speed, observed_at
            FROM observations
            {where}
            ORDER BY observed_at {order}, observation_id {order}
            LIMIT :limit
            """
        ),
        params,
    ).mappings()
    return [observation_row_to_dict(dict(row)) for row in rows]


def create_observation(
    conn: Connection,
    animal_id: str,
    device_id: str,
    latitude: float,
    longitude: float,
    speed: float,
    observed_at: datetime | None = None,
) -> dict[str, object]:
    observed_at = observed_at or datetime.now(timezone.utc)
    observation_id = f"OBS-SIM-{uuid4().hex[:18].upper()}"
    row = conn.execute(
        text(
            """
            INSERT INTO observations
            (observation_id, animal_id, device_id, latitude, longitude, speed, observed_at, location)
            VALUES (:observation_id, :animal_id, :device_id, :latitude, :longitude, :speed,
                    :observed_at, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))
            RETURNING observation_id, animal_id, device_id, latitude, longitude, speed, observed_at
            """
        ),
        {
            "observation_id": observation_id,
            "animal_id": animal_id,
            "device_id": device_id,
            "latitude": latitude,
            "longitude": longitude,
            "speed": speed,
            "observed_at": observed_at,
        },
    ).mappings().one()
    return observation_row_to_dict(dict(row))


def movement_for_animal(
    conn: Connection,
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 500,
    descending: bool = False,
) -> dict[str, object]:
    rows = _movement_rows(conn, animal_id, start_time, end_time, limit)
    points = []
    total_distance = 0.0
    for row in rows:
        distance = row.get("distance_from_previous_meters")
        if distance is not None:
            total_distance += float(distance)
        points.append(_movement_point_from_row(row))
    if descending:
        points.reverse()
    started_at = rows[0]["observed_at"] if rows else None
    ended_at = rows[-1]["observed_at"] if rows else None
    duration_seconds = (ended_at - started_at).total_seconds() if started_at and ended_at else 0
    return {
        "animal_id": animal_id,
        "points": points,
        "total_distance_meters": round(total_distance, 2),
        "movement_duration_seconds": max(0, duration_seconds),
        "started_at": started_at,
        "ended_at": ended_at,
        "point_count": len(points),
    }


def distance_for_animal(
    conn: Connection,
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 2000,
) -> dict[str, object]:
    movement = movement_for_animal(conn, animal_id, start_time, end_time, limit)
    return {
        "animal_id": animal_id,
        "total_distance_meters": movement["total_distance_meters"],
        "started_at": movement["started_at"],
        "ended_at": movement["ended_at"],
        "point_count": movement["point_count"],
    }


def zone_history_for_animal(
    conn: Connection,
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 2000,
) -> dict[str, object]:
    rows = _movement_rows(conn, animal_id, start_time, end_time, limit)
    if not rows:
        return {"animal_id": animal_id, "segments": [], "transitions": []}

    segments = []
    transitions = []
    active_zone = _zone_from_row(rows[0])
    active_entered_at = rows[0]["observed_at"]
    previous_zone = active_zone

    for row in rows[1:]:
        current_zone = _zone_from_row(row)
        if _zone_key(current_zone) == _zone_key(previous_zone):
            continue
        transitioned_at = row["observed_at"]
        segments.append(_zone_segment(active_zone, active_entered_at, transitioned_at))
        transitions.append(
            {
                "from_zone": previous_zone,
                "to_zone": current_zone,
                "transitioned_at": transitioned_at,
                "entered_at": transitioned_at,
            }
        )
        active_zone = current_zone
        previous_zone = current_zone
        active_entered_at = transitioned_at

    ended_at = rows[-1]["observed_at"]
    segments.append(_zone_segment(active_zone, active_entered_at, ended_at))
    for transition in transitions:
        matching_segment = next(
            (
                segment
                for segment in segments
                if segment["entered_at"] == transition["entered_at"]
                and _zone_key(segment["zone"]) == _zone_key(transition["to_zone"])
            ),
            None,
        )
        if matching_segment:
            transition["exited_at"] = matching_segment["exited_at"]
            transition["duration_seconds"] = matching_segment["duration_seconds"]
    return {"animal_id": animal_id, "segments": segments, "transitions": transitions}


def timeline_for_animal(
    conn: Connection,
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 2000,
) -> dict[str, object]:
    rows = _movement_rows(conn, animal_id, start_time, end_time, limit)
    events = []
    previous_zone = None
    for index, row in enumerate(rows):
        current_zone = _zone_from_row(row)
        if index and _zone_key(current_zone) != _zone_key(previous_zone):
            events.append(
                {
                    "event_type": "zone_transition",
                    "timestamp": row["observed_at"],
                    "from_zone": previous_zone,
                    "to_zone": current_zone,
                }
            )
        events.append(
            {
                "event_type": "observation",
                "timestamp": row["observed_at"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "zone": current_zone,
                "distance_from_previous_meters": float(row["distance_from_previous_meters"])
                if row.get("distance_from_previous_meters") is not None
                else 0,
            }
        )
        previous_zone = current_zone
    return {"animal_id": animal_id, "events": events}


def _movement_rows(
    conn: Connection,
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 500,
) -> list[dict[str, object]]:
    clauses = ["o.animal_id = :animal_id"]
    params: dict[str, object] = {"animal_id": animal_id, "limit": min(limit, 5000)}
    if start_time:
        clauses.append("o.observed_at >= :start_time")
        params["start_time"] = start_time
    if end_time:
        clauses.append("o.observed_at <= :end_time")
        params["end_time"] = end_time
    where = " AND ".join(clauses)
    rows = conn.execute(
        text(
            f"""
            WITH filtered AS (
                SELECT
                    o.observation_id, o.animal_id, o.device_id, o.latitude, o.longitude,
                    o.speed, o.observed_at, o.location,
                    z.zone_id, z.zone_name, z.zone_type, z.risk_level
                FROM observations o
                LEFT JOIN LATERAL (
                    SELECT * FROM zones WHERE ST_Covers(geometry, o.location)
                    ORDER BY CASE risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                             ST_Area(geometry), zone_id LIMIT 1
                ) z ON true
                WHERE {where}
                ORDER BY o.observed_at ASC, o.observation_id ASC
                LIMIT :limit
            ),
            ordered AS (
                SELECT
                    filtered.*,
                    LAG(location) OVER (ORDER BY observed_at ASC, observation_id ASC) AS previous_location
                FROM filtered
            )
            SELECT
                observation_id, animal_id, device_id, latitude, longitude, speed, observed_at,
                zone_id, zone_name, zone_type, risk_level,
                CASE
                    WHEN previous_location IS NULL THEN NULL
                    ELSE GREATEST(0, ST_Distance(location::geography, previous_location::geography))
                END AS distance_from_previous_meters
            FROM ordered
            ORDER BY observed_at ASC, observation_id ASC
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def _movement_point_from_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "observation_id": row["observation_id"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "timestamp": row["observed_at"],
        "speed": float(row["speed"]) if row.get("speed") is not None else None,
        "zone": _zone_from_row(row),
        "distance_from_previous_meters": float(row["distance_from_previous_meters"])
        if row.get("distance_from_previous_meters") is not None
        else 0,
    }


def _zone_key(zone: dict[str, object] | None) -> str | None:
    return str(zone["zone_id"]) if zone else None


def _zone_segment(zone: dict[str, object] | None, entered_at: datetime, exited_at: datetime | None) -> dict[str, object]:
    duration_seconds = (exited_at - entered_at).total_seconds() if exited_at else 0
    return {
        "zone": zone,
        "entered_at": entered_at,
        "exited_at": exited_at,
        "duration_seconds": max(0, duration_seconds),
    }
