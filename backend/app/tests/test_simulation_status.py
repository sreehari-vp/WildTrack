import unittest

from backend.app.services.simulation import MovementSimulator
from backend.app.services.simulation_config import SIMULATION_PATHS


class SimulationStatusTests(unittest.TestCase):
    def test_status_is_stopped_until_start_is_called(self):
        simulator = MovementSimulator()
        self.assertFalse(simulator.status().running)

    def test_status_includes_live_coordinates_for_each_route(self):
        status = MovementSimulator().status()
        self.assertEqual(set(status.animals), set(SIMULATION_PATHS))
        for animal_id, path in SIMULATION_PATHS.items():
            self.assertEqual(
                status.animals[animal_id].coordinates,
                [path[0].longitude, path[0].latitude],
            )


if __name__ == "__main__":
    unittest.main()
