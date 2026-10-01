import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.app.core.config import get_settings
from backend.app.db.mongodb.client import get_mongo_client, get_mongo_database
from backend.app.db.postgres.session import engine as app_engine
from backend.app.main import app
from backend.app.seed.mongodb_seed import seed_mongodb
from backend.app.seed.postgres_seed import seed_postgres
from backend.app.services.alerts import list_alerts
from backend.app.services.eca import evaluate_event, evaluate_observation_context, load_active_rules
from backend.app.services.observations import create_observation
from backend.app.services.spatial import zone_containing_point


class Phase5EcaAlertTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        settings = get_settings()
        cls.engine = create_engine(settings.sqlalchemy_migration_url, pool_pre_ping=True)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()
        app_engine.dispose()

    def setUp(self) -> None:
        seed_postgres()
        seed_mongodb()

    def test_active_eca_rules_load(self) -> None:
        with self.engine.connect() as conn:
            rules = load_active_rules(conn)
        rule_ids = {rule["rule_id"] for rule in rules}
        self.assertIn("RULE-001", rule_ids)
        self.assertIn("RULE-004", rule_ids)

    def test_restricted_zone_entry_creates_high_alert_and_mongo_event(self) -> None:
        alert = self._evaluate_observation("EL-001", 11.414, 76.651, previous_zone_id="ZONE-SAFE")[0]
        self.assertFalse(alert["duplicate"])
        self.assertEqual(alert["severity"], "high")
        self.assertEqual(alert["animal_id"], "EL-001")
        self.assertEqual(alert["zone_id"], "ZONE-RESTRICTED")

        mongo_client = get_mongo_client()
        try:
            db = get_mongo_database(mongo_client)
            event = db.boundary_events.find_one(
                {
                    "event_type": "restricted_zone_entry",
                    "animal_id": "EL-001",
                    "zone_id": "ZONE-RESTRICTED",
                    "alert_id": alert["alert_id"],
                    "metadata.source": "phase_5_eca",
                }
            )
            self.assertIsNotNone(event)
        finally:
            mongo_client.close()

    def test_duplicate_active_alert_is_not_created(self) -> None:
        first = self._evaluate_observation("EL-001", 11.414, 76.651, previous_zone_id="ZONE-SAFE")[0]
        second = self._evaluate_observation("EL-001", 11.414, 76.651, previous_zone_id="ZONE-SAFE")[0]
        with self.engine.connect() as conn:
            alerts = list_alerts(conn, animal_id="EL-001", zone_id="ZONE-RESTRICTED", status="open")
        self.assertEqual(first["alert_id"], second["alert_id"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(len([alert for alert in alerts if alert["rule_id"] == "RULE-001"]), 1)

    def test_different_animal_can_create_own_alert(self) -> None:
        alert = self._evaluate_observation("TG-002", 11.383, 76.692, previous_zone_id="ZONE-BUFFER")[0]
        self.assertEqual(alert["animal_id"], "TG-002")
        self.assertEqual(alert["zone_id"], "ZONE-PROTECTED")
        self.assertEqual(alert["rule_id"], "RULE-002")

    def test_high_risk_zone_entry_uses_critical_severity(self) -> None:
        alert = self._evaluate_observation("DR-001", 11.412, 76.704, previous_zone_id="ZONE-SAFE")[0]
        self.assertEqual(alert["rule_id"], "RULE-004")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["zone_id"], "ZONE-HIGH-RISK")

    def test_low_battery_rule_uses_device_context(self) -> None:
        alerts = self._evaluate_observation("DR-003", 11.388, 76.714, previous_zone_id="ZONE-PROTECTED")
        low_battery = [alert for alert in alerts if alert["rule_id"] == "RULE-003"]
        self.assertEqual(len(low_battery), 1)
        self.assertEqual(low_battery[0]["severity"], "medium")

    def test_no_alert_when_no_rule_matches(self) -> None:
        alerts = self._evaluate_observation("EL-001", 11.451, 76.644, previous_zone_id=None)
        self.assertEqual(alerts, [])

    def test_alert_resolution_api_and_already_resolved_handling(self) -> None:
        response = self.client.patch("/api/v1/alerts/ALT-001", json={"status": "resolved"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "resolved")
        self.assertIsNotNone(response.json()["resolved_at"])

        duplicate = self.client.patch("/api/v1/alerts/ALT-001", json={"status": "resolved"})
        self.assertEqual(duplicate.status_code, 409)

    def test_alert_filter_apis(self) -> None:
        self._evaluate_observation("EL-001", 11.414, 76.651, previous_zone_id="ZONE-SAFE")
        alerts = self.client.get("/api/v1/alerts?animal_id=EL-001&severity=high")
        self.assertEqual(alerts.status_code, 200)
        self.assertTrue(any(alert["zone_id"] == "ZONE-RESTRICTED" for alert in alerts.json()))

        animal_alerts = self.client.get("/api/v1/animals/EL-001/alerts")
        self.assertEqual(animal_alerts.status_code, 200)
        self.assertTrue(any(alert["rule_id"] == "RULE-001" for alert in animal_alerts.json()))

        zone_alerts = self.client.get("/api/v1/zones/ZONE-RESTRICTED/alerts")
        self.assertEqual(zone_alerts.status_code, 200)
        self.assertTrue(any(alert["animal_id"] == "EL-001" for alert in zone_alerts.json()))

    def test_mongodb_failure_does_not_block_postgres_alert(self) -> None:
        with self.engine.begin() as conn:
            event = self._event_for("EL-001", 11.414, 76.651, previous_zone_id="ZONE-SAFE", conn=conn)
            alerts = evaluate_event(conn, event, mongo_db=FailingMongoDatabase())
        self.assertEqual(len(alerts), 1)
        self.assertFalse(alerts[0]["duplicate"])

    def test_invalid_alert_status_and_missing_alert(self) -> None:
        invalid = self.client.patch("/api/v1/alerts/ALT-001", json={"status": "sleeping"})
        self.assertEqual(invalid.status_code, 400)
        missing = self.client.patch("/api/v1/alerts/UNKNOWN", json={"status": "resolved"})
        self.assertEqual(missing.status_code, 404)

    def _evaluate_observation(self, animal_id: str, latitude: float, longitude: float, previous_zone_id: str | None) -> list[dict[str, object]]:
        mongo_client = get_mongo_client()
        try:
            mongo_db = get_mongo_database(mongo_client)
            with self.engine.begin() as conn:
                animal = self._animal(conn, animal_id)
                observation = create_observation(
                    conn,
                    animal_id=animal["animal_id"],
                    device_id=animal["device_id"],
                    latitude=latitude,
                    longitude=longitude,
                    speed=4.0,
                    observed_at=datetime.now(timezone.utc),
                )
                zones = zone_containing_point(conn, longitude, latitude)
                return evaluate_observation_context(
                    conn,
                    animal=animal,
                    observation=observation,
                    current_zone=dict(zones[0]) if zones else None,
                    previous_zone_id=previous_zone_id,
                    mongo_db=mongo_db,
                )
        finally:
            mongo_client.close()

    def _event_for(
        self,
        animal_id: str,
        latitude: float,
        longitude: float,
        previous_zone_id: str | None,
        conn,
    ) -> dict[str, object]:
        animal = self._animal(conn, animal_id)
        observation = create_observation(
            conn,
            animal_id=animal["animal_id"],
            device_id=animal["device_id"],
            latitude=latitude,
            longitude=longitude,
            speed=4.0,
            observed_at=datetime.now(timezone.utc),
        )
        zones = zone_containing_point(conn, longitude, latitude)
        zone = dict(zones[0])
        return {
            "event_type": "restricted_zone_entry",
            "animal_id": animal["animal_id"],
            "animal_code": animal["animal_code"],
            "animal_name": animal["name"],
            "species": animal["species"],
            "device_id": animal["device_id"],
            "battery_level": animal["battery_level"],
            "observation_id": observation["observation_id"],
            "timestamp": observation["observed_at"],
            "latitude": latitude,
            "longitude": longitude,
            "previous_zone_id": previous_zone_id,
            "zone_id": zone["zone_id"],
            "zone_name": zone["zone_name"],
            "zone_type": zone["zone_type"],
            "risk_level": zone["risk_level"],
        }

    def _animal(self, conn, animal_id: str) -> dict[str, object]:
        row = conn.execute(
            text(
                """
                SELECT a.animal_id, a.animal_code, a.name, a.species, a.device_id, d.battery_level
                FROM animals a
                LEFT JOIN devices d ON d.device_id = a.device_id
                WHERE a.animal_id = :animal_id
                """
            ),
            {"animal_id": animal_id},
        ).mappings().one()
        return dict(row)


class FailingMongoCollection:
    def insert_one(self, document):
        raise RuntimeError("Mongo unavailable")


class FailingMongoDatabase:
    def __getitem__(self, name):
        return FailingMongoCollection()


if __name__ == "__main__":
    unittest.main()
