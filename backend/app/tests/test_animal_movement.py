"""Read-only movement checks against existing animals; no fixtures are inserted."""
import os
import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

@unittest.skipUnless(os.getenv("WILDTRACK_READONLY_CHECKS") == "1", "Read-only database checks are opt-in")
class AnimalMovementHardeningTest(unittest.TestCase):
    def test_existing_movement_invariants(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/animals")
            self.assertEqual(response.status_code, 200, response.text)
            for animal in response.json()[:5]:
                with self.subTest(animal=animal["animal_id"]):
                    result = client.get("/api/v1/animals/" + animal["animal_id"] + "/movement?limit=100")
                    self.assertEqual(result.status_code, 200, result.text)
                    movement = result.json()
                    self.assertEqual(movement["point_count"], len(movement["points"]))
                    self.assertGreaterEqual(movement["total_distance_meters"], 0)
                    times = [point["timestamp"] for point in movement["points"]]
                    self.assertEqual(times, sorted(times))
