import asyncio
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.app.core.config import get_settings
from backend.app.db.mongodb.client import get_mongo_client, get_mongo_database
from backend.app.db.postgres.session import engine as app_engine
from backend.app.main import app
from backend.app.seed.mongodb_seed import seed_mongodb
from backend.app.seed.postgres_seed import seed_postgres
from backend.app.services.simulation import simulator


class Phase3BackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        seed_postgres()
        seed_mongodb()
        settings = get_settings()
        cls.engine = create_engine(settings.sqlalchemy_migration_url, pool_pre_ping=True)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        asyncio.run(simulator.reset())
        cls.engine.dispose()
        app_engine.dispose()

    def test_phase3_end_to_end(self) -> None:
        with TestClient(app) as client:
            self._run_api_assertions(client)

    def _run_api_assertions(self, client: TestClient) -> None:
        animals = client.get("/api/v1/animals")
        self.assertEqual(animals.status_code, 200)
        self.assertGreaterEqual(len(animals.json()), 7)

        animal = client.get("/api/v1/animals/EL-001")
        self.assertEqual(animal.status_code, 200)
        self.assertEqual(animal.json()["animal_id"], "EL-001")

        missing = client.get("/api/v1/animals/UNKNOWN")
        self.assertEqual(missing.status_code, 404)

        location = client.get("/api/v1/animals/EL-001/location")
        self.assertEqual(location.status_code, 200)
        self.assertEqual(location.json()["current_zone"]["zone_id"], "ZONE-SAFE")

        observations = client.get("/api/v1/observations?animal_id=EL-001&limit=10")
        self.assertEqual(observations.status_code, 200)
        self.assertGreaterEqual(len(observations.json()), 1)

        movement = client.get("/api/v1/animals/EL-001/movement")
        self.assertEqual(movement.status_code, 200)
        self.assertEqual(movement.json()["animal_id"], "EL-001")

        zones = client.get("/api/v1/zones")
        self.assertEqual(zones.status_code, 200)
        self.assertEqual(len(zones.json()), 6)

        zone_lookup = client.get("/api/v1/zones/lookup?latitude=11.414&longitude=76.651")
        self.assertEqual(zone_lookup.status_code, 200)
        self.assertEqual(zone_lookup.json()["zone_id"], "ZONE-RESTRICTED")

        with self.engine.connect() as conn:
            before_count = conn.execute(text("SELECT COUNT(*) FROM observations")).scalar_one()

        start = client.post("/api/v1/simulation/start")
        self.assertEqual(start.status_code, 200)
        self.assertTrue(start.json()["started"])

        duplicate_start = client.post("/api/v1/simulation/start")
        self.assertEqual(duplicate_start.status_code, 200)
        self.assertFalse(duplicate_start.json()["started"])

        stop = client.post("/api/v1/simulation/stop")
        self.assertEqual(stop.status_code, 200)
        self.assertTrue(stop.json()["stopped"])

        asyncio.run(simulator.reset())
        for _ in range(6):
            asyncio.run(simulator.step_once())

        with self.engine.connect() as conn:
            after_count = conn.execute(text("SELECT COUNT(*) FROM observations")).scalar_one()
            latest_zone = conn.execute(
                text(
                    """
                    SELECT z.zone_id
                    FROM observations o
                    JOIN zones z ON ST_Contains(z.geometry, o.location)
                    WHERE o.animal_id = 'EL-001'
                    ORDER BY o.observed_at DESC
                    LIMIT 1
                    """
                )
            ).scalar_one()
        self.assertGreater(after_count, before_count)
        self.assertEqual(latest_zone, "ZONE-RESTRICTED")

        mongo_client = get_mongo_client()
        try:
            db = get_mongo_database(mongo_client)
            boundary_event = db.boundary_events.find_one(
                {
                    "event_type": "boundary_crossing",
                    "animal_id": "EL-001",
                    "to_zone_id": "ZONE-RESTRICTED",
                    "metadata.source": "phase_3_simulator",
                }
            )
            self.assertIsNotNone(boundary_event)
            forbidden = set(db.list_collection_names()) & {"animals", "devices", "zones", "observations", "eca_rules", "alerts"}
            self.assertEqual(forbidden, set())
        finally:
            mongo_client.close()

        refreshed_movement = client.get("/api/v1/animals/EL-001/movement?limit=50")
        self.assertEqual(refreshed_movement.status_code, 200)
        self.assertGreater(len(refreshed_movement.json()["points"]), 1)

        status = client.get("/api/v1/simulation/status")
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["running"])

        reset = client.post("/api/v1/simulation/reset")
        self.assertEqual(reset.status_code, 200)
        self.assertTrue(reset.json()["reset"])

        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
