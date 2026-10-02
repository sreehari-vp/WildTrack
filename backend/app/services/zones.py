import json

from sqlalchemy import text
from sqlalchemy.engine import Connection


def list_zones(conn: Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        text(
            """
            SELECT zone_id, zone_name, zone_type, risk_level, description, created_in_app, version_no,
                   ST_AsGeoJSON(geometry)::json AS geometry,
                   ST_Area(geometry::geography) / 1000000.0 AS area_km2
            FROM zones
            ORDER BY zone_name
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def get_zone(conn: Connection, zone_id: str) -> dict[str, object] | None:
    row = conn.execute(
        text(
            """
            SELECT zone_id, zone_name, zone_type, risk_level, description, created_in_app, version_no,
                   ST_AsGeoJSON(geometry)::json AS geometry,
                   ST_Area(geometry::geography) / 1000000.0 AS area_km2
            FROM zones
            WHERE zone_id = :zone_id
            """
        ),
        {"zone_id": zone_id},
    ).mappings().first()
    return dict(row) if row else None


def animals_currently_in_zone(conn: Connection, zone_id: str) -> list[dict[str, object]]:
    rows = conn.execute(
        text(
            """
            WITH latest_observation AS (
                SELECT DISTINCT ON (animal_id)
                    observation_id, animal_id, device_id AS observation_device_id,
                    latitude, longitude, speed, observed_at, location
                FROM observations
                ORDER BY animal_id, observed_at DESC, observation_id DESC
            )
            SELECT
                a.animal_id, a.animal_code, a.species, a.name, a.age, a.sex, a.status,
                d.device_id, d.device_code, d.device_type, d.status AS device_status,
                d.battery_level, d.last_seen,
                lo.observation_id, lo.observation_device_id, lo.latitude, lo.longitude,
                lo.speed, lo.observed_at,
                z.zone_id, z.zone_name, z.zone_type, z.risk_level
            FROM latest_observation lo
            JOIN LATERAL (
                SELECT * FROM zones WHERE ST_Covers(geometry, lo.location)
                ORDER BY CASE risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                         ST_Area(geometry), zone_id LIMIT 1
            ) z ON true
            JOIN animals a ON a.animal_id = lo.animal_id
            LEFT JOIN devices d ON d.device_id = a.device_id
            WHERE z.zone_id = :zone_id
            ORDER BY a.animal_code
            """
        ),
        {"zone_id": zone_id},
    ).mappings()
    return [_animal_from_row(dict(row)) for row in rows]


def recent_zone_transitions(conn: Connection, zone_id: str, limit: int = 20) -> list[dict[str, object]]:
    rows = conn.execute(
        text(
            """
            WITH observation_zones AS (
                SELECT
                    o.animal_id, a.animal_code, o.observed_at,
                    z.zone_id, z.zone_name, z.zone_type, z.risk_level,
                    LAG(z.zone_id) OVER (PARTITION BY o.animal_id ORDER BY o.observed_at ASC, o.observation_id ASC) AS previous_zone_id,
                    LAG(z.zone_name) OVER (PARTITION BY o.animal_id ORDER BY o.observed_at ASC, o.observation_id ASC) AS previous_zone_name,
                    LAG(z.zone_type) OVER (PARTITION BY o.animal_id ORDER BY o.observed_at ASC, o.observation_id ASC) AS previous_zone_type,
                    LAG(z.risk_level) OVER (PARTITION BY o.animal_id ORDER BY o.observed_at ASC, o.observation_id ASC) AS previous_risk_level
                FROM observations o
                JOIN animals a ON a.animal_id = o.animal_id
                LEFT JOIN LATERAL (
                    SELECT * FROM zones WHERE ST_Covers(geometry, o.location)
                    ORDER BY CASE risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                             ST_Area(geometry), zone_id LIMIT 1
                ) z ON true
            )
            SELECT *
            FROM observation_zones
            WHERE (zone_id = :zone_id OR previous_zone_id = :zone_id)
              AND (previous_zone_id IS DISTINCT FROM zone_id)
            ORDER BY observed_at DESC
            LIMIT :limit
            """
        ),
        {"zone_id": zone_id, "limit": min(limit, 100)},
    ).mappings()
    return [
        {
            "animal_id": row["animal_id"],
            "animal_code": row["animal_code"],
            "transitioned_at": row["observed_at"],
            "from_zone": _zone_summary(row, "previous_"),
            "to_zone": _zone_summary(row, ""),
        }
        for row in rows
    ]


def _animal_from_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "animal_id": row["animal_id"],
        "animal_code": row["animal_code"],
        "species": row["species"],
        "name": row["name"],
        "age": row["age"],
        "sex": row["sex"],
        "status": row["status"],
        "device": {
            "device_id": row["device_id"],
            "device_code": row["device_code"],
            "device_type": row["device_type"],
            "status": row["device_status"],
            "battery_level": row["battery_level"],
            "last_seen": row["last_seen"],
        }
        if row.get("device_id")
        else None,
        "latest_observation": {
            "observation_id": row["observation_id"],
            "animal_id": row["animal_id"],
            "device_id": row["observation_device_id"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "speed": float(row["speed"]),
            "observed_at": row["observed_at"],
        }
        if row.get("observation_id")
        else None,
        "current_zone": _zone_summary(row, ""),
    }


def _zone_summary(row: dict[str, object], prefix: str) -> dict[str, object] | None:
    zone_id = row.get(f"{prefix}zone_id")
    if not zone_id:
        return None
    return {
        "zone_id": zone_id,
        "name": row.get(f"{prefix}zone_name"),
        "zone_type": row.get(f"{prefix}zone_type"),
        "risk_level": row.get(f"{prefix}risk_level"),
    }
