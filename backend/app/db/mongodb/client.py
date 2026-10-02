from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from backend.app.core.config import get_settings


EVENT_COLLECTIONS = ("wildlife_events", "boundary_events", "sensor_events", "device_events")
FORBIDDEN_CORE_COLLECTIONS = {"animals", "devices", "zones", "observations", "eca_rules", "alerts"}


def get_mongo_client() -> MongoClient:
    settings = get_settings()
    return MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=6000)


def get_mongo_database(client: MongoClient | None = None) -> Database:
    settings = get_settings()
    mongo_client = client or get_mongo_client()
    return mongo_client[settings.mongodb_database]


def ensure_event_indexes(db: Database) -> None:
    for name in EVENT_COLLECTIONS:
        db[name].create_index([("event_id", ASCENDING)], unique=True, sparse=True)
    db.wildlife_events.create_index([("event_type", ASCENDING), ("timestamp", DESCENDING)])
    db.wildlife_events.create_index([("animal_id", ASCENDING), ("timestamp", DESCENDING)])

    db.boundary_events.create_index([("event_type", ASCENDING), ("timestamp", DESCENDING)])
    db.boundary_events.create_index([("animal_id", ASCENDING), ("timestamp", DESCENDING)])
    db.boundary_events.create_index([("from_zone_id", ASCENDING), ("to_zone_id", ASCENDING)])

    db.sensor_events.create_index([("event_type", ASCENDING), ("timestamp", DESCENDING)])
    db.sensor_events.create_index([("device_id", ASCENDING), ("timestamp", DESCENDING)])

    db.device_events.create_index([("event_type", ASCENDING), ("timestamp", DESCENDING)])
    db.device_events.create_index([("device_id", ASCENDING), ("timestamp", DESCENDING)])


def find_forbidden_core_collections(db: Database) -> list[str]:
    names = set(db.list_collection_names())
    return sorted(names & FORBIDDEN_CORE_COLLECTIONS)
