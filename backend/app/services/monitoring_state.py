"""Database operations for persistent map work."""

from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from backend.app.schemas.api import MapPreferences, PinWrite, ZoneWrite
from backend.app.services.zones import get_zone


def _validated_geometry(session: Session, geometry: dict, region_code: str | None = None) -> tuple[str, str]:
    import json

    encoded = json.dumps(geometry)
    try:
        matched_region = session.execute(text("""
            WITH input AS (
                SELECT ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326) AS geom
            )
            SELECT r.code
            FROM input i JOIN study_regions r ON ST_Covers(r.geometry, i.geom)
            WHERE ST_IsValid(i.geom) AND NOT ST_IsEmpty(i.geom)
              AND ST_Area(i.geom::geography) > 0
              AND ST_Covers((SELECT ST_Union(geometry) FROM forest_boundaries), i.geom)
              AND (:region_code IS NULL OR r.code = :region_code)
            ORDER BY ST_Area(r.geometry::geography), r.code
            LIMIT 1
        """), {"geometry": encoded, "region_code": region_code}).scalar_one_or_none()
    except DBAPIError:
        session.rollback()
        raise ValueError("Zone geometry is malformed") from None
    if not matched_region:
        if region_code:
            raise ValueError("Zone geometry must remain fully inside its assigned Ooty region")
        raise ValueError("Zone must be a valid polygon fully inside one Ooty region")
    return encoded, matched_region


def create_zone(session: Session, payload: ZoneWrite) -> dict:
    geometry, region_code = _validated_geometry(session, payload.geometry)
    zone_id = f"ZONE-{uuid4().hex[:20].upper()}"
    try:
        session.execute(text("""
            INSERT INTO zones (zone_id, zone_name, zone_type, risk_level, description, geometry, created_in_app, study_region_code)
            VALUES (:id, :name, :type, :risk, :description,
                    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326)), true, :region_code)
        """), {"id": zone_id, "name": payload.zone_name.strip(), "type": payload.zone_type,
               "risk": payload.risk_level, "description": payload.description, "geometry": geometry,
               "region_code": region_code})
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("A zone with this name already exists") from None
    return get_zone(session.connection(), zone_id)


def update_zone(session: Session, zone_id: str, payload: ZoneWrite) -> dict | None:
    existing = get_zone(session.connection(), zone_id)
    if not existing:
        return None
    geometry, region_code = _validated_geometry(session, payload.geometry, existing.get("study_region_code"))
    try:
        session.execute(text("""
            UPDATE zones SET zone_name=:name, zone_type=:type, risk_level=:risk,
                description=:description,
                geometry=ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326)),
                study_region_code=:region_code, updated_at=now()
            WHERE zone_id=:id
        """), {"id": zone_id, "name": payload.zone_name.strip(), "type": payload.zone_type,
               "risk": payload.risk_level, "description": payload.description, "geometry": geometry,
               "region_code": region_code})
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("A zone with this name already exists") from None
    return get_zone(session.connection(), zone_id)


def delete_zone(session: Session, zone_id: str) -> bool:
    result = session.execute(text("""
        DELETE FROM zones WHERE zone_id=:id AND created_in_app=true
          AND NOT EXISTS (SELECT 1 FROM alerts WHERE alerts.zone_id=zones.zone_id)
          AND NOT EXISTS (SELECT 1 FROM observations WHERE ST_Covers(zones.geometry, observations.location))
        RETURNING zone_id
    """), {"id": zone_id}).first()
    session.commit()
    return result is not None


def list_pins(session: Session) -> list[dict]:
    rows = session.execute(text("""
        SELECT pin_id AS id, name, pin_type AS type,
               ARRAY[ST_X(location), ST_Y(location)] AS coordinates, created_at
        FROM map_pins ORDER BY created_at DESC, pin_id
    """)).mappings()
    return [dict(row) for row in rows]


def create_pin(session: Session, payload: PinWrite) -> dict:
    pin_id = str(uuid4())
    row = session.execute(text("""
        INSERT INTO map_pins (pin_id, name, pin_type, location)
        VALUES (:id, :name, :type, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
        RETURNING pin_id AS id, name, pin_type AS type,
                  ARRAY[ST_X(location), ST_Y(location)] AS coordinates, created_at
    """), {"id": pin_id, "name": payload.name.strip(), "type": payload.type,
           "lon": payload.coordinates[0], "lat": payload.coordinates[1]}).mappings().one()
    session.commit()
    return dict(row)


def delete_pin(session: Session, pin_id: str) -> bool:
    result = session.execute(text("DELETE FROM map_pins WHERE pin_id=:id RETURNING pin_id"), {"id": pin_id}).first()
    session.commit()
    return result is not None


def get_preferences(session: Session) -> MapPreferences:
    settings = session.execute(text("SELECT settings FROM map_preferences WHERE preference_id='default'")).scalar_one_or_none()
    return MapPreferences.model_validate(settings) if settings else MapPreferences()


def save_preferences(session: Session, payload: MapPreferences) -> MapPreferences:
    import json

    session.execute(text("""
        INSERT INTO map_preferences (preference_id, settings) VALUES ('default', CAST(:settings AS jsonb))
        ON CONFLICT (preference_id) DO UPDATE SET settings=EXCLUDED.settings, updated_at=now()
        WHERE map_preferences.settings IS DISTINCT FROM EXCLUDED.settings
    """), {"settings": json.dumps(payload.model_dump())})
    session.commit()
    return payload
