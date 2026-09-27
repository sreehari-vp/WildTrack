from sqlalchemy import text

from backend.app.db.mongodb.client import get_mongo_client, get_mongo_database
from backend.app.db.postgres.session import engine


def postgres_health() -> dict[str, object]:
    try:
        with engine.connect() as conn:
            postgis_version = conn.execute(text("SELECT PostGIS_Version()")).scalar_one()
            conn.execute(text("SELECT 1")).scalar_one()
        return {"reachable": True, "postgis": True, "postgis_version": str(postgis_version)}
    except Exception as exc:
        return {"reachable": False, "postgis": False, "error": exc.__class__.__name__}


def mongodb_health() -> dict[str, object]:
    client = None
    try:
        client = get_mongo_client()
        db = get_mongo_database(client)
        client.admin.command("ping")
        return {"reachable": True, "database": db.name}
    except Exception as exc:
        return {"reachable": False, "error": exc.__class__.__name__}
    finally:
        if client is not None:
            client.close()


def database_health() -> dict[str, object]:
    postgres = postgres_health()
    mongodb = mongodb_health()
    return {
        "status": "ok" if postgres["reachable"] and mongodb["reachable"] else "degraded",
        "postgres": postgres,
        "mongodb": mongodb,
    }
