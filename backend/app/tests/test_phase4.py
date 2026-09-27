import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.app.core.config import get_settings
from backend.app.db.postgres.session import engine as app_engine
from backend.app.main import app
from backend.app.seed.postgres_seed import seed_postgres
from backend.app.services.spatial import spatial_index_status


class Phase4SpatialTemporalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        seed_postgres()
        settings = get_settings()
        cls.engine = create_engine(settings.sqlalchemy_migration_url, pool_pre_ping=True)
        cls._insert_phase4_observations()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()
        app_engine.dispose()

    @classmethod
    def _insert_phase4_observations(cls) -> None:
        rows = [
            ("OBS-P4-001", "EL-001", "DEV-E-001", 11.451000, 76.644000, 3.2, "2026-09-24T11:00:00+00:00"),
            ("OBS-P4-002", "EL-001", "DEV-E-001", 11.445000, 76.690000, 4.1, "2026-09-24T11:08:00+00:00"),
            ("OBS-P4-003", "EL-001", "DEV-E-001", 11.414000, 76.651000, 4.8, "2026-09-24T11:15:00+00:00"),
            ("OBS-P4-004", "EL-001", "DEV-E-001", 11.438000, 76.704000, 3.7, "2026-09-24T11:35:00+00:00"),
        ]
        with cls.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO observations
                    (observation_id, animal_id, device_id, latitude, longitude, speed, observed_at, location)
                    VALUES (:observation_id, :animal_id, :device_id, :latitude, :longitude, :speed,
                            CAST(:observed_at AS timestamptz),
                            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))
                    """
                ),
                [
                    {
                        "observation_id": row[0],
                        "animal_id": row[1],
                        "device_id": row[2],
                        "latitude": row[3],
                        "longitude": row[4],
                        "speed": row[5],
                        "observed_at": row[6],
                    }
                    for row in rows
                ],
            )

    def test_point_in_polygon_lookup(self) -> None:
        response = self.client.get("/api/v1/zones/lookup?latitude=11.414&longitude=76.651")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["zone_id"], "ZONE-RESTRICTED")

    def test_current_zone_detection(self) -> None:
        response = self.client.get("/api/v1/animals/EL-001/location")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_zone"]["zone_id"], "ZONE-BUFFER")

    def test_movement_history_ordering_and_distance(self) -> None:
        response = self.client.get("/api/v1/animals/EL-001/movement?limit=50")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        points = payload["points"]
        self.assertGreater(len(points), 2)
        timestamps = [point["timestamp"] for point in points]
        self.assertEqual(timestamps, sorted(timestamps))
        self.assertGreater(payload["total_distance_meters"], 0)
        self.assertTrue(any(point["distance_from_previous_meters"] for point in points[1:]))

    def test_zone_transition_detection_and_time_spent(self) -> None:
        response = self.client.get("/api/v1/animals/EL-001/zone-history?limit=50")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["segments"]), 2)
        self.assertGreaterEqual(len(payload["transitions"]), 1)
        transition_targets = {transition["to_zone"]["zone_id"] for transition in payload["transitions"] if transition["to_zone"]}
        self.assertIn("ZONE-RESTRICTED", transition_targets)
        self.assertTrue(all(segment["duration_seconds"] >= 0 for segment in payload["segments"]))

    def test_timeline_contains_observations_and_transitions(self) -> None:
        response = self.client.get("/api/v1/animals/EL-001/timeline?limit=50")
        self.assertEqual(response.status_code, 200)
        event_types = {event["event_type"] for event in response.json()["events"]}
        self.assertIn("observation", event_types)
        self.assertIn("zone_transition", event_types)

    def test_distance_endpoint(self) -> None:
        response = self.client.get("/api/v1/animals/EL-001/distance?limit=50")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(payload["total_distance_meters"], 0)
        self.assertGreater(payload["point_count"], 1)

    def test_empty_movement_history(self) -> None:
        response = self.client.get(
            "/api/v1/animals/EL-001/movement?start_time=2099-01-01T00:00:00Z&end_time=2099-01-02T00:00:00Z"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["points"], [])
        self.assertEqual(payload["total_distance_meters"], 0)

    def test_invalid_animal_and_date_range(self) -> None:
        missing = self.client.get("/api/v1/animals/UNKNOWN/movement")
        self.assertEqual(missing.status_code, 404)
        invalid_range = self.client.get(
            "/api/v1/animals/EL-001/movement?start_time=2026-09-25T00:00:00Z&end_time=2026-09-24T00:00:00Z"
        )
        self.assertEqual(invalid_range.status_code, 400)

    def test_nearby_queries_and_zone_animals(self) -> None:
        zones = self.client.get("/api/v1/zones/nearby?latitude=11.414&longitude=76.651&radius_meters=500")
        self.assertEqual(zones.status_code, 200)
        self.assertIn("ZONE-RESTRICTED", {zone["zone_id"] for zone in zones.json()})

        animals = self.client.get("/api/v1/animals/nearby?latitude=11.414&longitude=76.651&radius_meters=5000")
        self.assertEqual(animals.status_code, 200)
        self.assertTrue(any(animal["animal_id"] in {"EL-001", "EL-002"} for animal in animals.json()))

        zone_animals = self.client.get("/api/v1/zones/ZONE-RESTRICTED/animals")
        self.assertEqual(zone_animals.status_code, 200)
        self.assertIn("EL-002", {animal["animal_id"] for animal in zone_animals.json()})

    def test_spatial_indexes_present(self) -> None:
        with self.engine.connect() as conn:
            indexes = set(spatial_index_status(conn))
        self.assertIn("ix_observations_location_gist", indexes)
        self.assertIn("ix_zones_geometry_gist", indexes)
        self.assertIn("ix_forest_boundaries_geometry_gist", indexes)


if __name__ == "__main__":
    unittest.main()
