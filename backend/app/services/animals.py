from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _zone_from_row(row: dict[str, object]) -> dict[str, object] | None:
    if not row.get("zone_id"):
        return None
    return {
        "zone_id": row["zone_id"],
        "name": row["zone_name"],
        "zone_type": row["zone_type"],
        "risk_level": row["risk_level"],
    }


def _observation_from_row(row: dict[str, object]) -> dict[str, object] | None:
    if not row.get("observation_id"):
        return None
    return {
        "observation_id": row["observation_id"],
        "animal_id": row["animal_id"],
        "device_id": row["observation_device_id"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "speed": float(row["speed"]),
        "observed_at": row["observed_at"],
    }


def _animal_from_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "animal_id": row["animal_id"],
        "animal_code": row["animal_code"],
        "species": row["species"],
        "name": row["name"],
        "age": row["age"],
        "sex": row["sex"],
        "status": row["status"],
        "data_origin": row["data_origin"],
        "source_reference_type": row["source_reference_type"],
        "source_reference_id": row["source_reference_id"],
        "source_reference_name": row["source_reference_name"],
        "source_reference_url": row["source_reference_url"],
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
        "latest_observation": _observation_from_row(row),
        "current_zone": _zone_from_row(row),
    }


ANIMAL_QUERY = """
WITH latest_observation AS (
    SELECT DISTINCT ON (animal_id)
        observation_id, animal_id, device_id AS observation_device_id, latitude, longitude, speed, observed_at, location
    FROM observations
    ORDER BY animal_id, observed_at DESC, observation_id DESC
)
SELECT
    a.animal_id, a.animal_code, a.species, a.name, a.age, a.sex, a.status,
    a.data_origin, a.source_reference_type, a.source_reference_id, a.source_reference_name, a.source_reference_url,
    d.device_id, d.device_code, d.device_type, d.status AS device_status, d.battery_level, d.last_seen,
    lo.observation_id, lo.observation_device_id, lo.latitude, lo.longitude, lo.speed, lo.observed_at,
    z.zone_id, z.zone_name, z.zone_type, z.risk_level
FROM animals a
LEFT JOIN devices d ON d.device_id = a.device_id
LEFT JOIN latest_observation lo ON lo.animal_id = a.animal_id
LEFT JOIN LATERAL (
                    SELECT * FROM zones WHERE ST_Covers(geometry, lo.location)
                    ORDER BY CASE risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                             ST_Area(geometry), zone_id LIMIT 1
                ) z ON true
"""


def list_animals(conn: Connection) -> list[dict[str, object]]:
    has_v2 = conn.execute(text("select exists(select 1 from animals where animal_id like 'SIM-V2-%')")).scalar_one()
    active_filter = " WHERE a.animal_id LIKE 'SIM-V2-%'" if has_v2 else ""
    rows = conn.execute(text(f"{ANIMAL_QUERY}{active_filter} ORDER BY a.animal_code")).mappings()
    return [_animal_from_row(dict(row)) for row in rows]


def get_animal(conn: Connection, animal_ref: str) -> dict[str, object] | None:
    row = conn.execute(
        text(f"{ANIMAL_QUERY} WHERE a.animal_id = :animal_ref OR a.animal_code = :animal_ref LIMIT 1"),
        {"animal_ref": animal_ref},
    ).mappings().first()
    return _animal_from_row(dict(row)) if row else None


def resolve_animal_id(conn: Connection, animal_ref: str) -> str | None:
    return conn.execute(
        text("SELECT animal_id FROM animals WHERE animal_id = :animal_ref OR animal_code = :animal_ref"),
        {"animal_ref": animal_ref},
    ).scalar_one_or_none()


def update_device_seen(conn: Connection, device_id: str, observed_at: datetime) -> None:
    conn.execute(
        text("UPDATE devices SET last_seen = :observed_at, updated_at = now() WHERE device_id = :device_id"),
        {"device_id": device_id, "observed_at": observed_at},
    )
