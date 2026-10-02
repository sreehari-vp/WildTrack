from __future__ import annotations

from datetime import datetime, timezone

from backend.app.db.mongodb.client import EVENT_COLLECTIONS, ensure_event_indexes, find_forbidden_core_collections, get_mongo_client, get_mongo_database


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


EVENTS = {
    "wildlife_events": [
        {
            "event_type": "unusual_movement",
            "animal_id": "EL-002",
            "timestamp": dt("2026-09-24T10:11:30"),
            "metadata": {"speed": 18.5, "duration": 120, "reason": "unusual_speed"},
        },
        {
            "event_type": "wildlife_activity",
            "animal_id": "TG-001",
            "timestamp": dt("2026-09-24T10:10:30"),
            "metadata": {"activity": "territorial_patrol", "confidence": 0.82},
        },
    ],
    "boundary_events": [
        {
            "event_type": "boundary_crossing",
            "animal_id": "EL-002",
            "timestamp": dt("2026-09-24T10:11:00"),
            "from_zone_id": "ZONE-SAFE",
            "to_zone_id": "ZONE-RESTRICTED",
            "location": {"lat": 11.414, "lng": 76.651},
            "metadata": {"speed": 4.8},
        },
        {
            "event_type": "boundary_crossing",
            "animal_id": "TG-001",
            "timestamp": dt("2026-09-24T10:10:00"),
            "from_zone_id": "ZONE-WATER",
            "to_zone_id": "ZONE-PROTECTED",
            "location": {"lat": 11.383, "lng": 76.692},
            "metadata": {"speed": 6.3},
        },
    ],
    "sensor_events": [
        {
            "event_type": "temperature_anomaly",
            "device_id": "DEV-T-001",
            "timestamp": dt("2026-09-24T10:07:00"),
            "metadata": {"temperature": 42.5, "threshold": 40},
        },
        {
            "event_type": "motion_detected",
            "device_id": "DEV-D-001",
            "timestamp": dt("2026-09-24T10:04:00"),
            "metadata": {"motion_score": 0.76},
        },
    ],
    "device_events": [
        {
            "event_type": "low_battery",
            "device_id": "DEV-D-003",
            "timestamp": dt("2026-09-24T10:05:00"),
            "metadata": {"battery_level": 18},
        },
        {
            "event_type": "gps_signal_lost",
            "device_id": "DEV-D-003",
            "timestamp": dt("2026-09-24T10:06:00"),
            "metadata": {"last_fix_seconds_ago": 420},
        },
    ],
}


def seed_mongodb() -> None:
    client = get_mongo_client()
    db = get_mongo_database(client)
    forbidden = find_forbidden_core_collections(db)
    if forbidden:
        raise RuntimeError(f"MongoDB contains forbidden core collections: {', '.join(forbidden)}")
    for collection_name in EVENT_COLLECTIONS:
        for event in EVENTS[collection_name]:
            # Match the immutable seed document; preserve existing event history.
            db[collection_name].update_one(event, {"$setOnInsert": event}, upsert=True)
    ensure_event_indexes(db)
    client.close()


if __name__ == "__main__":
    seed_mongodb()
    print("MongoDB event seed complete.")
