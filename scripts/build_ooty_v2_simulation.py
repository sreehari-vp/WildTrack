"""Build a reproducible 75-animal scenario whose routes cross Ooty zones."""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/research/ooty-v2"
CATALOG = DIRECTORY / "mammal-species-catalog.json"
SEED = 20261019
HABITAT_TYPES = {"tree_cover", "grassland", "surface_water", "cultivated_land", "built_up", "bare_or_sparse_cover"}
PREFERRED_GRASSLAND = {"Nilgiri tahr", "Sambar deer", "Asian elephant", "Gaur", "Wild boar"}
FIXES_PER_ZONE = 4
MAX_ZONE_GAP_M = 80


def point_dict(point: Point, region: str, zone_code: str) -> dict:
    return {"longitude": round(point.x, 6), "latitude": round(point.y, 6),
            "region_code": region, "zone_code": zone_code}


def inner_point(component, boundary_point: Point, toward: Point, meters: float = 15) -> Point:
    """Move a boundary point into its source polygon while retaining the zone."""
    line = LineString([boundary_point, toward])
    if line.length == 0:
        return component.representative_point()
    latitude = boundary_point.y
    fraction = min(0.25, meters / max(line.length * 111_000, meters))
    for attempt in range(12):
        candidate = line.interpolate(min(0.95, fraction * (2 ** attempt)))
        if component.covers(candidate):
            return candidate
    return component.representative_point()


def make_zone_walk(region: str, region_nodes: list[dict], preferred: str, rng: random.Random) -> list[dict]:
    nodes = []
    for feature in region_nodes:
        geometry = feature["geometry"]
        parts = sorted(getattr(geometry, "geoms", [geometry]), key=lambda part: part.area, reverse=True)
        for component in parts[:12]:
            if component.area > 0:
                nodes.append({"code": feature["code"], "type": feature["type"],
                              "geometry": component, "center": component.representative_point()})
    if not nodes:
        raise ValueError(f"No usable land-cover polygons for {region}")

    adjacency: dict[int, list[tuple[int, Point, Point]]] = defaultdict(list)
    for left_index, left in enumerate(nodes):
        for right_index in range(left_index + 1, len(nodes)):
            right = nodes[right_index]
            if left["code"] == right["code"]:
                continue
            distance_m = left["geometry"].distance(right["geometry"]) * 111_000
            if distance_m > MAX_ZONE_GAP_M:
                continue
            a, b = nearest_points(left["geometry"], right["geometry"])
            adjacency[left_index].append((right_index, a, b))
            adjacency[right_index].append((left_index, b, a))

    start_candidates = [i for i, node in enumerate(nodes)
                        if node["type"] == preferred and adjacency.get(i)]
    start_candidates = start_candidates or [i for i, node in enumerate(nodes) if adjacency.get(i)]
    if not start_candidates:
        raise ValueError(f"No touching land-cover zones for {region}")

    start = rng.choice(start_candidates)
    chain = [start]
    connectors: list[tuple[Point, Point]] = []
    for _ in range(3):
        current = chain[-1]
        candidates = [(next_index, a, b) for next_index, a, b in adjacency[current]
                      if next_index not in chain]
        if not candidates:
            candidates = [(next_index, a, b) for next_index, a, b in adjacency[current]
                          if nodes[next_index]["code"] != nodes[current]["code"]]
        if not candidates:
            break
        next_index, source_edge, target_edge = rng.choice(candidates)
        chain.append(next_index)
        connectors.append((source_edge, target_edge))

    if len({nodes[index]["code"] for index in chain}) < 2:
        raise ValueError(f"Route did not reach a second zone in {region}")

    route: list[dict] = []
    for position, node_index in enumerate(chain):
        node = nodes[node_index]
        if position == 0:
            _, exit_edge = connectors[position]
            start_point = inner_point(node["geometry"], exit_edge, node["center"], 120)
            end_point = inner_point(node["geometry"], connectors[position][0], node["center"], 15)
        elif position == len(chain) - 1:
            entry_edge = connectors[position - 1][1]
            start_point = inner_point(node["geometry"], entry_edge, node["center"], 15)
            end_point = node["center"]
        else:
            entry_edge = connectors[position - 1][1]
            exit_edge = connectors[position][0]
            start_point = inner_point(node["geometry"], entry_edge, node["center"], 15)
            end_point = inner_point(node["geometry"], exit_edge, node["center"], 15)

        # Every recorded fix belongs to this land-cover component. The interior
        # anchors make movement visible before each boundary crossing.
        candidates = [start_point]
        for fraction in (0.35, 0.70):
            origin = start_point if fraction == 0.35 else node["center"]
            target = node["center"] if fraction == 0.35 else end_point
            candidate = LineString([origin, target]).interpolate(fraction, normalized=True) if origin.distance(target) else origin
            if not node["geometry"].covers(candidate):
                candidate = node["center"]
            candidates.append(candidate)
        candidates.append(end_point)
        route.extend(point_dict(point, region, node["code"]) for point in candidates)

    if len(route) < 8:
        raise ValueError(f"Generated route too short to demonstrate zone crossings: {region}")
    return route


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    region_features = json.loads((DIRECTORY / "study-regions.geojson").read_text(encoding="utf-8"))["features"]
    zone_features = json.loads((DIRECTORY / "landcover-zones.geojson").read_text(encoding="utf-8"))["features"]
    from shapely.geometry import shape

    regions = [feature["properties"]["code"] for feature in region_features]
    zone_map = defaultdict(list)
    for feature in zone_features:
        props = feature["properties"]
        if props["zone_type"] in HABITAT_TYPES:
            zone_map[props["region_code"]].append({
                "code": props["code"], "type": props["zone_type"], "geometry": shape(feature["geometry"]),
            })

    rng = random.Random(SEED)
    region_counts: Counter[str] = Counter()
    region_species: Counter[tuple[str, str]] = Counter()
    assignments = []
    for species in sorted(catalog["species"], key=lambda item: -item["illustrative_count"]):
        for _ in range(species["illustrative_count"]):
            region = min(regions, key=lambda code: (
                region_species[(code, species["scientific_name"])], region_counts[code], rng.random()))
            assignments.append((region, species))
            region_counts[region] += 1
            region_species[(region, species["scientific_name"])] += 1
    rng.shuffle(assignments)

    animals = []
    route_zone_counts: Counter[str] = Counter()
    crossings = []
    for index, (region, species) in enumerate(assignments, start=1):
        preferred = "grassland" if species["common_name"] in PREFERRED_GRASSLAND else "tree_cover"
        route = make_zone_walk(region, zone_map[region], preferred, rng)
        visited = list(dict.fromkeys(point["zone_code"] for point in route))
        if len(visited) < 2:
            raise ValueError(f"{species['common_name']} route does not cross multiple zones")
        route_zone_counts.update(visited)
        crossings.append(len(visited))
        first = route[0]
        animals.append({
            "animal_id": f"SIM-V2-{index:03d}",
            "common_name": species["common_name"],
            "scientific_name": species["scientific_name"],
            "region_code": region,
            "zone_code": first["zone_code"],
            "location": {"type": "Point", "coordinates": [first["longitude"], first["latitude"]]},
            "route": route,
            "data_origin": "synthetic_scenario_from_regional_species_list",
            "source_references": catalog["sources"][:2],
            "location_note": "Synthetic scenario route crossing mapped ESA WorldCover classes; not telemetry or a wildlife sighting.",
        })

    if len(animals) != 75 or len({animal["scientific_name"] for animal in animals}) != 16:
        raise ValueError("The scenario must contain 75 trackers across 16 mammal species")
    if max(region_counts.values()) - min(region_counts.values()) > 1:
        raise ValueError("Scenario animals are not balanced across the eight regions")
    route_lengths = [len(animal["route"]) for animal in animals]
    if max(route_lengths) > 16 or min(route_lengths) < 8:
        raise ValueError("Routes must last 24–45 seconds at the configured 3-second GPS interval")

    output = {
        "title": "WildTrack Ooty V2 simulation scenario",
        "random_seed": SEED,
        "animal_count": len(animals),
        "species_count": len({animal["scientific_name"] for animal in animals}),
        "region_counts": dict(sorted(region_counts.items())),
        "route_zone_counts": dict(sorted(route_zone_counts.items())),
        "min_unique_zones_per_route": min(crossings),
        "mean_unique_zones_per_route": round(sum(crossings) / len(crossings), 2),
        "route_steps": {"min": min(route_lengths), "max": max(route_lengths), "seconds_per_fix": 3,
                        "duration_seconds": {"min": (min(route_lengths) - 1) * 3,
                                             "max": (max(route_lengths) - 1) * 3}},
        "data_origin": "synthetic_scenario_from_regional_species_list",
        "animals": animals,
    }
    path = DIRECTORY / "simulated-mammals.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in (
        "animal_count", "species_count", "region_counts", "min_unique_zones_per_route",
        "mean_unique_zones_per_route", "route_steps")}, indent=2))


if __name__ == "__main__":
    main()
