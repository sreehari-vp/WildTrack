from datetime import datetime
from typing import Any

from pymongo.database import Database


def events_by_animal(db: Database, animal_id: str) -> list[dict[str, Any]]:
    return list(db.wildlife_events.find({"animal_id": animal_id}, {"_id": False})) + list(
        db.boundary_events.find({"animal_id": animal_id}, {"_id": False})
    )


def events_by_device(db: Database, device_id: str) -> list[dict[str, Any]]:
    return list(db.sensor_events.find({"device_id": device_id}, {"_id": False})) + list(
        db.device_events.find({"device_id": device_id}, {"_id": False})
    )


def events_since(db: Database, timestamp: datetime) -> dict[str, int]:
    return {
        name: db[name].count_documents({"timestamp": {"$gte": timestamp}})
        for name in ("wildlife_events", "boundary_events", "sensor_events", "device_events")
    }
