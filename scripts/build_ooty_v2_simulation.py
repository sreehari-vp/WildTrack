"""Build a balanced 75-tracker scenario in source-derived Ooty land-cover zones.

The species list is regional context. Every identity, point and route here is
synthetic and must never be displayed as a sourced wildlife observation.
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/research/ooty-v2"
CATALOG = DIRECTORY / "mammal-species-catalog.json"
SEED = 20261019
HABITAT_TYPES = {"tree_cover", "grassland"}
GRASSLAND_SPECIES = {"Nilgiri tahr", "Sambar deer", "Asian elephant", "Gaur", "Wild boar"}


def sample_point(geometry, rng: random.Random) -> tuple[float, float]:
    polygons = [part for part in getattr(geometry, "geoms", [geometry]) if part.area > 0]
    polygons.sort(key=lambda part: part.area, reverse=True)
    # Larger components avoid placing synthetic pins in tiny mapping slivers.
    polygons = polygons[: min(20, len(polygons))]
    for _ in range(20_000):
        part = rng.choices(polygons, weights=[polygon.area for polygon in polygons], k=1)[0]
        minx, miny, maxx, maxy = part.bounds
        point = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        if part.covers(point):
            return round(point.x, 6), round(point.y, 6)
    raise RuntimeError("Could not sample a point inside selected land-cover zone")


def local_step(geometry, longitude: float, latitude: float, rng: random.Random) -> tuple[float, float]:
    for distance_m in (180, 90, 40):
        for _ in range(80):
            bearing = rng.random() * math.tau
            candidate = (
                round(longitude + math.sin(bearing) * distance_m / (111_320 * math.cos(math.radians(latitude))), 6),
                round(latitude + math.cos(bearing) * distance_m / 110_540, 6),
            )
            if geometry.covers(Point(candidate)):
                return candidate
    return longitude, latitude


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    region_features = json.loads((DIRECTORY / "study-regions.geojson").read_text(encoding="utf-8"))["features"]
    zone_features = json.loads((DIRECTORY / "landcover-zones.geojson").read_text(encoding="utf-8"))["features"]
    regions = [feature["properties"]["code"] for feature in region_features]
    zones = {(feature["properties"]["region_code"], feature["properties"]["zone_type"]): feature for feature in zone_features}
    rng = random.Random(SEED)
    region_counts: Counter[str] = Counter()
    region_species: Counter[tuple[str, str]] = Counter()
    assignments = []
    for species in sorted(catalog["species"], key=lambda item: -item["illustrative_count"]):
        for _ in range(species["illustrative_count"]):
            region = min(regions, key=lambda code: (region_species[(code, species["scientific_name"])], region_counts[code], rng.random()))
            assignments.append((region, species))
            region_counts[region] += 1
            region_species[(region, species["scientific_name"])] += 1
    rng.shuffle(assignments)

    animals = []
    zone_counts: Counter[str] = Counter()
    for index, (region, species) in enumerate(assignments, start=1):
        preferred = "grassland" if species["common_name"] in GRASSLAND_SPECIES else "tree_cover"
        available = [kind for kind in HABITAT_TYPES if (region, kind) in zones]
        zone_type = preferred if preferred in available else available[0]
        feature = zones[(region, zone_type)]
        geometry = shape(feature["geometry"])
        longitude, latitude = sample_point(geometry, rng)
        zone_code = feature["properties"]["code"]
        zone_counts[zone_code] += 1
        route = [{"longitude": longitude, "latitude": latitude, "region_code": region, "zone_code": zone_code}]
        for _ in range(12):
            waypoint_lon, waypoint_lat = local_step(geometry, route[-1]["longitude"], route[-1]["latitude"], rng)
            route.append({"longitude": waypoint_lon, "latitude": waypoint_lat, "region_code": region, "zone_code": zone_code})
        animals.append({
            "animal_id": f"SIM-V2-{index:03d}",
            "common_name": species["common_name"],
            "scientific_name": species["scientific_name"],
            "region_code": region,
            "zone_code": zone_code,
            "location": {"type": "Point", "coordinates": [longitude, latitude]},
            "route": route,
            "data_origin": "synthetic_scenario_from_regional_species_list",
            "source_references": [catalog["sources"][0], catalog["sources"][1]],
            "location_note": "Generated inside a modelled land-cover class; not a verified sighting, tracked animal, or habitat-use claim.",
        })
    if len(animals) != 75 or len({row["scientific_name"] for row in animals}) != 16:
        raise ValueError("The balanced scenario must contain 75 trackers across 16 species")
    if max(region_counts.values()) - min(region_counts.values()) > 1:
        raise ValueError("Scenario animals are not balanced across the eight regions")
    output = {
        "title": "WildTrack Ooty V2 simulation scenario",
        "random_seed": SEED,
        "animal_count": len(animals),
        "species_count": len({row["scientific_name"] for row in animals}),
        "region_counts": dict(sorted(region_counts.items())),
        "zone_counts": dict(sorted(zone_counts.items())),
        "data_origin": "synthetic_scenario_from_regional_species_list",
        "animals": animals,
    }
    path = DIRECTORY / "simulated-mammals.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"animals": len(animals), "species": output["species_count"], "regions": output["region_counts"], "zone_count": len(zone_counts), "output": str(path)}, indent=2))


if __name__ == "__main__":
    main()
