import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.app.core.config import get_settings
from backend.app.db.postgres.session import engine as app_engine
from backend.app.main import app
from backend.app.seed.postgres_seed import seed_postgres


class AnimalMovementHardeningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        seed_postgres()
        settings = get_settings()
        cls.engine = create_engine(settings.sqlalchemy_migration_url, pool_pre_ping=True)
        cls._insert_test_animals()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()
        app_engine.dispose()

    @classmethod
    def _insert_test_animals(cls) -> None:
        devices = [
            ("DEV-MOVE-001", "WT-MOVE-001", "gps_collar", "online", 91, "2026-09-24T10:05:00+00:00"),
            ("DEV-SINGLE-001", "WT-SINGLE-001", "gps_collar", "online", 88, "2026-09-24T12:00:00+00:00"),
            ("DEV-NOOBS-001", "WT-NOOBS-001", "gps_collar", "online", 77, None),
            ("DEV-TIE-001", "WT-TIE-001", "gps_collar", "online", 81, "2026-09-24T13:00:00+00:00"),
        ]
        animals = [
            ("TEST-MOVE", "TEST-MOVE", "elephant", "Movement Test", 12, "female", "active", "DEV-MOVE-001"),
            ("TEST-SINGLE", "TEST-SINGLE", "deer", "Single Point", 5, "female", "active", "DEV-SINGLE-001"),
            ("TEST-NOOBS", "TEST-NOOBS", "tiger", "No Observations", 8, "male", "active", "DEV-NOOBS-001"),
            ("TEST-TIE", "TEST-TIE", "elephant", "Tie Break", 14, "female", "active", "DEV-TIE-001"),
        ]
        observations = [
            ("OBS-MOVE-A", "TEST-MOVE", "DEV-MOVE-001", 11.451000, 76.644000, 2.0, "2026-09-24T10:00:00+00:00"),
            ("OBS-MOVE-B", "TEST-MOVE", "DEV-MOVE-001", 11.451000, 76.644000, 0.0, "2026-09-24T10:00:00+00:00"),
            ("OBS-MOVE-C", "TEST-MOVE", "DEV-MOVE-001", 11.414000, 76.651000, 3.0, "2026-09-24T10:05:00+00:00"),
            ("OBS-SINGLE-A", "TEST-SINGLE", "DEV-SINGLE-001", 11.444000, 76.633000, 1.2, "2026-09-24T12:00:00+00:00"),
            ("OBS-TIE-A", "TEST-TIE", "DEV-TIE-001", 11.414000, 76.651000, 1.8, "2026-09-24T13:00:00+00:00"),
            ("OBS-TIE-Z", "TEST-TIE", "DEV-TIE-001", 11.445000, 76.690000, 2.2, "2026-09-24T13:00:00+00:00"),
        ]
        with cls.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO devices (device_id, device_code, device_type, status, battery_level, last_seen)
                    VALUES (:device_id, :device_code, :device_type, :status, :battery_level, CAST(:last_seen AS timestamptz))
                    """
                ),
                [
                    {
                        "device_id": row[0],
                        "device_code": row[1],
                        "device_type": row[2],
                        "status": row[3],
                        "battery_level": row[4],
                        "last_seen": row[5],
                    }
                    for row in devices
                ],
            )
            conn.execute(
                text(
                    """
                    INSERT INTO animals (animal_id, animal_code, species, name, age, sex, status, device_id)
                    VALUES (:animal_id, :animal_code, :species, :name, :age, :sex, :status, :device_id)
                    """
                ),
                [
                    {
                        "animal_id": row[0],
                        "animal_code": row[1],
                        "species": row[2],
                        "name": row[3],
                        "age": row[4],
                        "sex": row[5],
                        "status": row[6],
                        "device_id": row[7],
                    }
                    for row in animals
                ],
            )
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
                    for row in observations
                ],
            )

    def test_current_location_uses_latest_deterministic_observation(self) -> None:
        response = self.client.get("/api/v1/animals/TEST-MOVE/location")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["observed_at"], "2026-09-24T10:05:00Z")
        self.assertEqual(payload["current_zone"]["zone_id"], "ZONE-RESTRICTED")
        self.assertEqual(payload["latitude"], 11.414)
        self.assertEqual(payload["longitude"], 76.651)

    def test_movement_order_distance_duration_and_coordinate_order(self) -> None:
        response = self.client.get("/api/v1/animals/TEST-MOVE/movement?limit=20")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        points = payload["points"]

        self.assertEqual(payload["point_count"], 3)
        self.assertEqual([point["observation_id"] for point in points], ["OBS-MOVE-A", "OBS-MOVE-B", "OBS-MOVE-C"])
        self.assertEqual(points[0]["distance_from_previous_meters"], 0)
        self.assertEqual(points[1]["distance_from_previous_meters"], 0)
        self.assertGreater(points[2]["distance_from_previous_meters"], 0)
        self.assertEqual(payload["movement_duration_seconds"], 300)
        self.assertGreater(payload["total_distance_meters"], 0)
        self.assertEqual([points[0]["longitude"], points[0]["latitude"]], [76.644, 11.451])

    def test_zone_history_deduplicates_repeated_zone_and_calculates_time(self) -> None:
        response = self.client.get("/api/v1/animals/TEST-MOVE/zone-history?limit=20")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(len(payload["transitions"]), 1)
        transition = payload["transitions"][0]
        self.assertEqual(transition["from_zone"]["zone_id"], "ZONE-SAFE")
        self.assertEqual(transition["to_zone"]["zone_id"], "ZONE-RESTRICTED")
        self.assertEqual(transition["entered_at"], "2026-09-24T10:05:00Z")

        safe_segment = payload["segments"][0]
        self.assertEqual(safe_segment["zone"]["zone_id"], "ZONE-SAFE")
        self.assertEqual(safe_segment["duration_seconds"], 300)
        self.assertEqual(payload["segments"][-1]["duration_seconds"], 0)

    def test_timeline_contains_ordered_observations_and_transition(self) -> None:
        response = self.client.get("/api/v1/animals/TEST-MOVE/timeline?limit=20")
        self.assertEqual(response.status_code, 200)
        events = response.json()["events"]
        self.assertEqual(events[0]["event_type"], "observation")
        self.assertEqual(events[1]["event_type"], "observation")
        self.assertEqual(events[2]["event_type"], "zone_transition")
        self.assertEqual(events[3]["event_type"], "observation")

    def test_single_observation_has_zero_distance_duration_and_no_transition(self) -> None:
        movement = self.client.get("/api/v1/animals/TEST-SINGLE/movement")
        self.assertEqual(movement.status_code, 200)
        movement_payload = movement.json()
        self.assertEqual(movement_payload["point_count"], 1)
        self.assertEqual(movement_payload["total_distance_meters"], 0)
        self.assertEqual(movement_payload["movement_duration_seconds"], 0)
        self.assertEqual(movement_payload["points"][0]["distance_from_previous_meters"], 0)

        history = self.client.get("/api/v1/animals/TEST-SINGLE/zone-history")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["transitions"], [])

    def test_no_observations_returns_clean_location_and_empty_movement(self) -> None:
        location = self.client.get("/api/v1/animals/TEST-NOOBS/location")
        self.assertEqual(location.status_code, 404)
        self.assertEqual(location.json()["detail"], "No location available for animal")

        movement = self.client.get("/api/v1/animals/TEST-NOOBS/movement")
        self.assertEqual(movement.status_code, 200)
        payload = movement.json()
        self.assertEqual(payload["points"], [])
        self.assertEqual(payload["point_count"], 0)
        self.assertEqual(payload["total_distance_meters"], 0)
        self.assertEqual(payload["movement_duration_seconds"], 0)

    def test_empty_future_range_invalid_animal_and_invalid_date_range(self) -> None:
        future = self.client.get(
            "/api/v1/animals/TEST-MOVE/movement?start_time=2099-01-01T00:00:00Z&end_time=2099-01-02T00:00:00Z"
        )
        self.assertEqual(future.status_code, 200)
        self.assertEqual(future.json()["point_count"], 0)

        missing = self.client.get("/api/v1/animals/NOT-A-REAL-ID/movement")
        self.assertEqual(missing.status_code, 404)

        invalid = self.client.get(
            "/api/v1/animals/TEST-MOVE/movement?start_time=2026-09-25T00:00:00Z&end_time=2026-09-24T00:00:00Z"
        )
        self.assertEqual(invalid.status_code, 400)

    def test_duplicate_timestamp_latest_tie_breaks_by_observation_id(self) -> None:
        response = self.client.get("/api/v1/animals/TEST-TIE/location")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["current_zone"]["zone_id"], "ZONE-BUFFER")
        self.assertEqual(payload["latitude"], 11.445)
        self.assertEqual(payload["longitude"], 76.69)


if __name__ == "__main__":
    unittest.main()
