import json
import unittest

from scripts.generate_simulated_population import CHECKLIST, REGION_ORDER, REGIONS, build_population, covers


class SimulatedPopulationTests(unittest.TestCase):
    def test_population_is_mammal_only_and_uses_regional_checklist_sources(self):
        population = build_population(75)
        self.assertEqual(population["count"], 75)
        self.assertEqual({animal["taxonomic_class"] for animal in population["animal_records"]}, {"Mammalia"})
        self.assertEqual(len(population["species_distribution"]), 13)
        self.assertEqual(sum(population["species_distribution"].values()), 75)
        self.assertEqual({animal["data_origin"] for animal in population["animal_records"]}, {"simulated_from_regional_species_list"})
        self.assertTrue(all(animal["source_reference_type"] == "regional_species_checklist" for animal in population["animal_records"]))
        self.assertTrue(all(animal["source_reference_url"].startswith("https://") for animal in population["animal_records"]))

    def test_population_covers_all_six_regions_and_routes_stay_inside_them(self):
        population = build_population(75)
        features = json.loads(REGIONS.read_text(encoding="utf-8"))["features"]
        geometries = {feature["properties"]["code"]: feature["geometry"] for feature in features}
        animals = {animal["animal_id"]: animal for animal in population["animal_records"]}
        self.assertEqual(set(population["region_distribution"]), set(REGION_ORDER))
        self.assertTrue(all(value > 0 for value in population["region_distribution"].values()))
        for animal_id, route in population["routes"].items():
            region = geometries[animals[animal_id]["seed_region"]]
            self.assertEqual(len(route), 72)
            self.assertTrue(all(covers(region, lon, lat) for lon, lat in route))

    def test_checklist_contains_the_requested_flagship_mammals(self):
        checklist = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        names = {animal["common_name"] for animal in checklist["animals"]}
        self.assertTrue({"Sambar deer", "Barking deer", "Nilgiri tahr", "Asian elephant", "Bengal tiger", "Indian leopard"}.issubset(names))


if __name__ == "__main__":
    unittest.main()
