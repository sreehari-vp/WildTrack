"""Pure rule checks; no database connection or writes."""
import unittest
from backend.app.services.eca import conditions_match, observation_events

class Phase5EcaAlertTest(unittest.TestCase):
    def test_battery_threshold(self):
        self.assertTrue(conditions_match({"battery_level_lt": 25}, {"battery_level": 24}))
        self.assertFalse(conditions_match({"battery_level_lt": 25}, {"battery_level": 25}))
        self.assertFalse(conditions_match({"battery_level_lt": 25}, {}))

    def test_unknown_conditions_fail_closed(self):
        self.assertFalse(conditions_match({"unknown_condition": True}, {}))

    def test_zone_events_require_a_transition(self):
        args = dict(animal={"animal_id": "A"}, observation={}, current_zone={"zone_id": "Z", "zone_type": "restricted"})
        entered = observation_events(**args, previous_zone_id=None)
        self.assertIn("restricted_zone_entry", [event["event_type"] for event in entered])
        unchanged = observation_events(**args, previous_zone_id="Z")
        self.assertEqual(unchanged, [])

    def test_species_and_zone_conditions_both_required(self):
        conditions = {"species": "tiger", "zone_type": "protected"}
        self.assertTrue(conditions_match(conditions, {"species": "tiger", "zone_type": "protected"}))
        self.assertFalse(conditions_match(conditions, {"species": "deer", "zone_type": "protected"}))
