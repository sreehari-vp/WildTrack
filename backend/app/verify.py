from __future__ import annotations

from datetime import datetime, timezone
from pprint import pformat

from sqlalchemy import create_engine, inspect, text

from backend.app.core.config import get_settings
from backend.app.db.mongodb.client import EVENT_COLLECTIONS, ensure_event_indexes, find_forbidden_core_collections, get_mongo_client, get_mongo_database
from backend.app.services.event_store import events_by_animal, events_by_device, events_since
from backend.app.services.spatial import distance_between_observations, latest_animal_zones, zone_containing_point


EXPECTED_TABLES = {
    "animals",
    "devices",
    "zones",
    "observations",
    "eca_rules",
    "alerts",
    "forest_boundaries",
}


def verify_postgres() -> dict[str, object]:
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_migration_url, pool_pre_ping=True)
    result: dict[str, object] = {}
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        result["connected"] = True
        result["postgis_version"] = conn.execute(text("SELECT PostGIS_Version()")).scalar_one()
        result["tables_present"] = sorted(tables & EXPECTED_TABLES)
        result["missing_tables"] = sorted(EXPECTED_TABLES - tables)
        result["row_counts"] = {
            table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in sorted(EXPECTED_TABLES)
        }
        result["foreign_keys"] = {
            table: len(inspector.get_foreign_keys(table))
            for table in ("animals", "observations", "alerts")
        }
        result["point_in_polygon"] = zone_containing_point(conn, 76.651, 11.414)
        result["latest_animal_zones"] = latest_animal_zones(conn)
        result["distance_meters"] = distance_between_observations(conn, "OBS-001", "OBS-005")
        result["movement_history_rows"] = conn.execute(
            text("SELECT COUNT(*) FROM observations WHERE animal_id = 'EL-002'")
        ).scalar_one()
        result["open_alerts"] = conn.execute(text("SELECT COUNT(*) FROM alerts WHERE status = 'open'")).scalar_one()
        result["gist_indexes"] = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND indexdef ILIKE '%USING gist%'
                    ORDER BY indexname
                    """
                )
            )
        ]
    return result


def verify_mongodb() -> dict[str, object]:
    client = get_mongo_client()
    try:
        db = get_mongo_database(client)
        client.admin.command("ping")
        ensure_event_indexes(db)
        collections = set(db.list_collection_names())
        result: dict[str, object] = {
            "connected": True,
            "database": db.name,
            "collections_present": sorted(collections & set(EVENT_COLLECTIONS)),
            "missing_collections": sorted(set(EVENT_COLLECTIONS) - collections),
            "forbidden_core_collections": find_forbidden_core_collections(db),
            "row_counts": {name: db[name].count_documents({}) for name in EVENT_COLLECTIONS},
            "animal_event_count": len(events_by_animal(db, "EL-002")),
            "device_event_count": len(events_by_device(db, "DEV-D-003")),
            "events_since_counts": events_since(db, datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc)),
            "indexes": {name: sorted(db[name].index_information().keys()) for name in EVENT_COLLECTIONS},
        }
        return result
    finally:
        client.close()


def main() -> None:
    report = {
        "postgres": verify_postgres(),
        "mongodb": verify_mongodb(),
    }
    print(pformat(report, sort_dicts=False))


if __name__ == "__main__":
    main()
