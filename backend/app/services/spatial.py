from sqlalchemy import text
from sqlalchemy.engine import Connection


def zone_containing_point(conn: Connection, longitude: float, latitude: float) -> list[dict[str, object]]:
    rows = conn.execute(
        text(
            """
            SELECT zone_id, zone_name, zone_type, risk_level
            FROM zones
            WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))
            ORDER BY zone_name
            """
        ),
        {"longitude": longitude, "latitude": latitude},
    ).mappings()
    return [dict(row) for row in rows]


def latest_animal_zones(conn: Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        text(
            """
            WITH latest_observation AS (
                SELECT DISTINCT ON (animal_id)
                    animal_id, location, observed_at
                FROM observations
                ORDER BY animal_id, observed_at DESC
            )
            SELECT a.animal_id, a.animal_code, a.species, z.zone_id, z.zone_name, latest_observation.observed_at
            FROM latest_observation
            JOIN animals a ON a.animal_id = latest_observation.animal_id
            LEFT JOIN zones z ON ST_Contains(z.geometry, latest_observation.location)
            ORDER BY a.animal_code
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def distance_between_observations(conn: Connection, observation_a: str, observation_b: str) -> float | None:
    return conn.execute(
        text(
            """
            SELECT ST_Distance(a.location::geography, b.location::geography) AS meters
            FROM observations a
            JOIN observations b ON b.observation_id = :observation_b
            WHERE a.observation_id = :observation_a
            """
        ),
        {"observation_a": observation_a, "observation_b": observation_b},
    ).scalar_one_or_none()


def animals_near_location(conn: Connection, longitude: float, latitude: float, radius_meters: float = 1000) -> list[dict[str, object]]:
    rows = conn.execute(
        text(
            """
            WITH latest_observation AS (
                SELECT DISTINCT ON (animal_id)
                    animal_id, latitude, longitude, observed_at, location
                FROM observations
                ORDER BY animal_id, observed_at DESC
            ),
            origin AS (
                SELECT ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography AS geog
            )
            SELECT
                a.animal_id, a.animal_code, a.species, a.name,
                lo.latitude, lo.longitude, lo.observed_at,
                ST_Distance(lo.location::geography, origin.geog) AS distance_meters
            FROM latest_observation lo
            JOIN animals a ON a.animal_id = lo.animal_id
            CROSS JOIN origin
            WHERE ST_DWithin(lo.location::geography, origin.geog, :radius_meters)
            ORDER BY distance_meters ASC, a.animal_code
            """
        ),
        {"longitude": longitude, "latitude": latitude, "radius_meters": radius_meters},
    ).mappings()
    return [
        {
            "animal_id": row["animal_id"],
            "animal_code": row["animal_code"],
            "species": row["species"],
            "name": row["name"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "observed_at": row["observed_at"],
            "distance_meters": float(row["distance_meters"]),
        }
        for row in rows
    ]


def zones_near_location(conn: Connection, longitude: float, latitude: float, radius_meters: float = 1000) -> list[dict[str, object]]:
    rows = conn.execute(
        text(
            """
            WITH origin AS (
                SELECT ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography AS geog
            )
            SELECT
                z.zone_id, z.zone_name, z.zone_type, z.risk_level,
                ST_Distance(z.geometry::geography, origin.geog) AS distance_meters
            FROM zones z
            CROSS JOIN origin
            WHERE ST_DWithin(z.geometry::geography, origin.geog, :radius_meters)
            ORDER BY distance_meters ASC, z.zone_name
            """
        ),
        {"longitude": longitude, "latitude": latitude, "radius_meters": radius_meters},
    ).mappings()
    return [
        {
            "zone_id": row["zone_id"],
            "zone_name": row["zone_name"],
            "zone_type": row["zone_type"],
            "risk_level": row["risk_level"],
            "distance_meters": float(row["distance_meters"]),
        }
        for row in rows
    ]


def spatial_index_status(conn: Connection) -> list[str]:
    rows = conn.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename IN ('observations', 'zones', 'forest_boundaries')
              AND indexdef ILIKE '%USING gist%'
            ORDER BY indexname
            """
        )
    ).scalars()
    return list(rows)
