"""Read-only API checks against the configured application database.
Set WILDTRACK_READONLY_CHECKS=1 to opt in. Never seeds or resets records.
"""
import os
import unittest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from backend.app.main import app

@unittest.skipUnless(os.getenv("WILDTRACK_READONLY_CHECKS") == "1", "Read-only database checks are opt-in")
class Phase3BackendTest(unittest.TestCase):
    def test_api_contracts(self):
        with TestClient(app) as client:
            for path in ("/animals", "/observations?limit=5", "/zones", "/alerts?limit=5"):
                with self.subTest(path=path):
                    response = client.get("/api/v1" + path)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertIsInstance(response.json(), list)
            boundary = client.get("/api/v1/boundaries")
            self.assertEqual(boundary.status_code, 200, boundary.text)
            self.assertEqual(boundary.json()["type"], "MultiPolygon")
            analytics = client.get("/api/v1/analytics")
            self.assertEqual(analytics.status_code, 200, analytics.text)
            self.assertEqual(analytics.json()["source"], "PostgreSQL / PostGIS")
            self.assertEqual(len(analytics.json()["hourlyActivity"]), 24)

            end = datetime.now(timezone.utc)
            filtered = client.get("/api/v1/analytics", params={
                "start_time": (end - timedelta(days=7)).isoformat(),
                "end_time": end.isoformat(),
                "species": "elephant",
            })
            self.assertEqual(filtered.status_code, 200, filtered.text)
            filtered_data = filtered.json()
            self.assertTrue(all(row["name"] == "Elephant" for row in filtered_data["speciesActivity"]))
            self.assertTrue(all(row["tigers"] == 0 and row["deer"] == 0 for row in filtered_data["hourlyActivity"]))

            invalid_species = client.get("/api/v1/analytics", params={"species": "unknown"})
            self.assertEqual(invalid_species.status_code, 422)
            reversed_range = client.get("/api/v1/analytics", params={
                "start_time": end.isoformat(),
                "end_time": (end - timedelta(days=1)).isoformat(),
            })
            self.assertEqual(reversed_range.status_code, 400)
