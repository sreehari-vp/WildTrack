"""Movement graph projection checks; no Aura or database writes."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.services.movement_network import build_daily_corridors, sync_projection


def fix(animal: str, zone: str | None, minute: int, species: str = "deer") -> dict:
    return {
        "animal_id": animal, "zone_id": zone, "species": species,
        "observed_at": datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minute),
    }


class MovementNetworkTest(unittest.TestCase):
    def test_repeated_fixes_and_outside_points_do_not_inflate_corridors(self):
        days, uses, edges = build_daily_corridors([
            fix("A1", "Z1", 0), fix("A1", "Z1", 1), fix("A1", None, 2),
            fix("A1", "Z2", 3), fix("A1", "Z2", 4), fix("A1", "Z1", 5),
            fix("A2", "Z1", 0), fix("A2", "Z2", 6),
        ])
        self.assertEqual(len(days), 2)
        self.assertEqual(len(uses), 3)
        forward = next(edge for edge in edges if edge["from_zone_id"] == "Z1")
        self.assertEqual(forward["crossings"], 2)
        self.assertEqual(forward["animals"], 2)
        self.assertEqual(next(edge for edge in edges if edge["from_zone_id"] == "Z2")["crossings"], 1)

    def test_long_gap_does_not_invent_a_corridor(self):
        _, _, edges = build_daily_corridors([fix("A1", "Z1", 0), fix("A1", "Z2", 6 * 60 + 1)])
        self.assertEqual(edges, [])

    def test_crossing_uses_utc_day(self):
        local_time = timezone(timedelta(hours=5, minutes=30))
        rows = [
            {"animal_id": "A1", "zone_id": "Z1", "species": "deer",
             "observed_at": datetime(2026, 10, 2, 0, 5, tzinfo=local_time)},
            {"animal_id": "A1", "zone_id": "Z2", "species": "deer",
             "observed_at": datetime(2026, 10, 2, 0, 10, tzinfo=local_time)},
        ]
        days, _, _ = build_daily_corridors(rows)
        self.assertEqual(days[0]["date"], "2026-10-01")

    def test_projection_activates_only_after_all_graph_writes(self):
        source = {
            "signature": "fixed", "observation_count": 2,
            "zones": [
                {"zone_id": "Z1", "zone_name": "One", "zone_type": "safe", "risk_level": "low", "version_no": 1, "retired": False},
                {"zone_id": "Z2", "zone_name": "Two", "zone_type": "safe", "risk_level": "low", "version_no": 1, "retired": False},
            ],
            "animals": [{"animal_id": "A1", "animal_code": "DR-001", "name": "Doe", "species": "deer"}],
            "days": [{"date": "2026-10-01", "from_zone_id": "Z1", "to_zone_id": "Z2", "crossings": 1, "animals": 1, "last_at": "2026-10-01T00:01:00+00:00"}],
            "animal_days": [{"date": "2026-10-01", "from_zone_id": "Z1", "to_zone_id": "Z2", "animal_id": "A1", "species": "deer", "count": 1, "first_at": "2026-10-01T00:01:00+00:00", "last_at": "2026-10-01T00:01:00+00:00"}],
            "edges": [{"from_zone_id": "Z1", "to_zone_id": "Z2", "crossings": 1, "animals": 1, "last_at": "2026-10-01T00:01:00+00:00"}],
        }
        statements = []
        session = MagicMock()

        def run(query, **_params):
            statements.append(query)
            result = MagicMock()
            if "RETURN p.active_generation AS generation" in query:
                result.single.return_value = None
            elif "DETACH DELETE n" in query:
                result.consume.return_value.counters.nodes_deleted = 0
            return result

        session.run.side_effect = run
        driver = MagicMock()
        driver.session.return_value.__enter__.return_value = session
        with patch("backend.app.services.movement_network.configured", return_value=True), patch(
            "backend.app.services.movement_network.read_source_projection", return_value=source
        ), patch("backend.app.services.movement_network.get_driver", return_value=driver), patch(
            "backend.app.services.movement_network.get_settings", return_value=SimpleNamespace(neo4j_database="neo4j")
        ), patch("backend.app.services.movement_network._acquire_global_sync_lock", return_value=MagicMock()), patch(
            "backend.app.services.movement_network._release_global_sync_lock"
        ):
            result = sync_projection()
        self.assertTrue(result["changed"])
        activation = next(i for i, query in enumerate(statements) if "SET p.active_generation" in query)
        self.assertGreater(activation, next(i for i, query in enumerate(statements) if "WILDTRACK_CORRIDOR" in query))


if __name__ == "__main__":
    unittest.main()
