"""Generate a rough mammal-only simulated population for the Ooty/Nilgiris study areas.

The checklist supports regional species presence; it is not a census. Animal IDs,
initial coordinates, and routes are synthetic. Run without --apply to produce and
inspect a manifest only. Database import requires migration 0008.
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from math import cos, radians, sin
from pathlib import Path

from sqlalchemy import create_engine, text

from backend.app.core.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "data/research/nilgiris-mammal-checklist.json"
REGIONS = ROOT / "data/research/phase1-study-regions.geojson"
OUTPUT = ROOT / "data/research/simulation-population.json"
SEED = 20261018
REGION_ORDER = ("mukurthi", "upper_bhavani", "avalanche", "pykara", "ooty_north", "doddabetta")


def _on_segment(x: float, y: float, a: list[float], b: list[float]) -> bool:
    cross = (x - a[0]) * (b[1] - a[1]) - (y - a[1]) * (b[0] - a[0])
    if abs(cross) > 1e-10:
        return False
    return min(a[0], b[0]) - 1e-10 <= x <= max(a[0], b[0]) + 1e-10 and min(a[1], b[1]) - 1e-10 <= y <= max(a[1], b[1]) + 1e-10


def _ring_covers(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    for a, b in zip(ring, ring[1:]):
        if _on_segment(x, y, a, b):
            return True
        if (a[1] > y) != (b[1] > y):
            crossing_x = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < crossing_x:
                inside = not inside
    return inside


def covers(geometry: dict, longitude: float, latitude: float) -> bool:
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    for polygon in polygons:
        if not polygon or not _ring_covers(longitude, latitude, polygon[0]):
            continue
        if not any(_ring_covers(longitude, latitude, hole) for hole in polygon[1:]):
            return True
    return False


def _polygon_parts(geometry: dict) -> list[list]:
    return geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]


def sample_point(geometry: dict, rng: random.Random) -> tuple[float, float]:
    parts = _polygon_parts(geometry)
    weighted = []
    for polygon in parts:
        ring = polygon[0]
        xs, ys = [point[0] for point in ring], [point[1] for point in ring]
        weight = max((max(xs) - min(xs)) * (max(ys) - min(ys)), 1e-12)
        weighted.append((polygon, weight))
    for _ in range(50000):
        polygon = rng.choices([item[0] for item in weighted], weights=[item[1] for item in weighted], k=1)[0]
        ring = polygon[0]
        xs, ys = [point[0] for point in ring], [point[1] for point in ring]
        lon = rng.uniform(min(xs), max(xs))
        lat = rng.uniform(min(ys), max(ys))
        if covers(geometry, lon, lat):
            return round(lon, 6), round(lat, 6)
    raise RuntimeError("Could not sample a point inside a study region")


def make_route(start: tuple[float, float], geometry: dict, rng: random.Random, steps: int = 72) -> list[list[float]]:
    lon, lat = start
    route = [[lon, lat]]
    for _ in range(steps - 1):
        next_point = None
        for distance in (rng.uniform(100, 260), rng.uniform(35, 110)):
            for _attempt in range(80):
                bearing = rng.random() * 2 * 3.141592653589793
                next_lat = lat + distance * cos(bearing) / 110540
                next_lon = lon + distance * sin(bearing) / (111320 * cos(radians(lat)))
                if covers(geometry, next_lon, next_lat):
                    next_point = (round(next_lon, 6), round(next_lat, 6))
                    break
            if next_point:
                break
        if not next_point:
            break
        lon, lat = next_point
        route.append([lon, lat])
    return route


def _species_counts(species: list[dict], count: int) -> list[dict]:
    total_weight = sum(item["population_weight"] for item in species)
    exact = [item["population_weight"] * count / total_weight for item in species]
    counts = [int(value) for value in exact]
    for index in sorted(range(len(exact)), key=lambda i: exact[i] - counts[i], reverse=True)[:count - sum(counts)]:
        counts[index] += 1
    return [item for item, amount in zip(species, counts) for _ in range(amount)]


def build_population(count: int) -> dict:
    rng = random.Random(SEED)
    checklist = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    features = json.loads(REGIONS.read_text(encoding="utf-8"))["features"]
    region_features = {feature["properties"]["code"]: feature for feature in features}
    geometries = {code: feature["geometry"] for code, feature in region_features.items()}
    species = checklist["animals"]
    selected = _species_counts(species, count)
    rng.shuffle(selected)
    region_counts = {code: 0 for code in REGION_ORDER}
    animals, routes = [], {}
    for index, record in enumerate(selected, start=1):
        available_regions = [code for code in record["habitat_regions"] if code in geometries]
        if not available_regions:
            raise RuntimeError(f"No study region configured for {record['scientific_name']}")
        # Rotate across all six areas, choosing only from each species' coarse checklist range.
        preferred = REGION_ORDER[(index - 1) % len(REGION_ORDER)]
        if preferred in available_regions:
            region = preferred
        else:
            region = min(available_regions, key=lambda code: (region_counts[code], code))
        region_counts[region] += 1
        animal_id = f"SIM-{index:03d}"
        start = sample_point(geometries[region], rng)
        reference = region_features[region]["properties"]
        animals.append({
            "animal_id": animal_id,
            "animal_code": animal_id,
            "species": record["scientific_name"],
            "common_name": record["common_name"],
            "taxonomic_class": "Mammalia",
            "name": f"{record['common_name']} {index:03d}",
            "status": "active",
            "data_origin": "simulated_from_regional_species_list",
            "source_reference_type": "regional_species_checklist",
            "source_reference_id": record["source_id"],
            "source_reference_name": record["source_title"],
            "source_reference_url": record["source_url"],
            "seed_region": region,
            "seed_region_name": reference["name"],
            "device_id": f"SIM-DEV-{index:03d}",
            "initial_location": {"longitude": start[0], "latitude": start[1]},
        })
        routes[animal_id] = make_route(start, geometries[region], rng)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": SEED,
        "count": len(animals),
        "species_source": checklist["title"],
        "scope_note": checklist["scope_note"],
        "simulation_mix_note": checklist["simulation_mix_note"],
        "sources": checklist["sources"],
        "region_distribution": region_counts,
        "species_distribution": {record["scientific_name"]: sum(a["species"] == record["scientific_name"] for a in animals) for record in species},
        "simulation_notice": "Synthetic animal identities, starting positions, and movements. The checklist supports regional species presence only; it is not a current census or animal tracking dataset.",
        "animal_records": animals,
        "routes": routes,
    }


def apply_population(population: dict) -> int:
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_migration_url, pool_pre_ping=True)
    now = datetime.now(timezone.utc)
    inserted = 0
    with engine.begin() as conn:
        for animal in population["animal_records"]:
            device = animal["device_id"]
            conn.execute(text("""
                INSERT INTO devices (device_id, device_code, device_type, status, battery_level, last_seen)
                VALUES (:id, :code, 'simulated_gps', 'online', 100, :now)
                ON CONFLICT (device_id) DO UPDATE
                SET device_type = EXCLUDED.device_type, status = 'online', last_seen = EXCLUDED.last_seen
            """), {"id": device, "code": device, "now": now})
            created = conn.execute(text("""
                INSERT INTO animals (animal_id, animal_code, species, name, status, device_id,
                                     data_origin, source_occurrence_id, source_occurrence_url,
                                     source_reference_type, source_reference_id, source_reference_name, source_reference_url)
                VALUES (:id, :code, :species, :name, 'active', :device,
                        'simulated_from_regional_species_list', NULL, NULL,
                        'regional_species_checklist', :source_id, :source_name, :source_url)
                ON CONFLICT (animal_id) DO UPDATE SET
                    animal_code = EXCLUDED.animal_code,
                    species = EXCLUDED.species,
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    device_id = EXCLUDED.device_id,
                    data_origin = EXCLUDED.data_origin,
                    source_occurrence_id = NULL,
                    source_occurrence_url = NULL,
                    source_reference_type = EXCLUDED.source_reference_type,
                    source_reference_id = EXCLUDED.source_reference_id,
                    source_reference_name = EXCLUDED.source_reference_name,
                    source_reference_url = EXCLUDED.source_reference_url,
                    updated_at = now()
                RETURNING animal_id
            """), {"id": animal["animal_id"], "code": animal["animal_code"],
                  "species": animal["species"], "name": animal["name"], "device": device,
                  "source_id": animal["source_reference_id"], "source_name": animal["source_reference_name"],
                  "source_url": animal["source_reference_url"]}).scalar_one_or_none()
            if created:
                inserted += 1
            location = animal["initial_location"]
            conn.execute(text("""
                INSERT INTO observations
                    (observation_id, animal_id, device_id, latitude, longitude, location, speed, observed_at)
                VALUES (:obs, :animal, :device, :lat, :lon,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 0, :now)
                ON CONFLICT (observation_id) DO UPDATE SET
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    location = EXCLUDED.location,
                    speed = 0,
                    observed_at = EXCLUDED.observed_at
            """), {"obs": f"OBS-SIM-{animal['animal_id']}", "animal": animal["animal_id"],
                  "device": device, "lat": location["latitude"], "lon": location["longitude"], "now": now})
    engine.dispose()
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=75, help="synthetic wildlife tracker count (default: 75)")
    parser.add_argument("--apply", action="store_true", help="insert or refresh SIM-* synthetic animals in PostgreSQL")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not 1 <= args.count <= 500:
        parser.error("--count must be between 1 and 500")
    population = build_population(args.count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(population, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {args.count} simulated mammals: {len(population['species_distribution'])} species across {sum(v > 0 for v in population['region_distribution'].values())} regions.")
    print(f"Species mix: {population['species_distribution']}")
    print(f"Region mix: {population['region_distribution']}")
    print(f"Manifest: {args.output}")
    if args.apply:
        inserted = apply_population(population)
        print(f"Inserted or refreshed {inserted} SIM-* animal records. Existing non-SIM wildlife records were not changed.")
    else:
        print("Database unchanged. Review the manifest, migrate to 0008, then rerun with --apply to refresh the simulation population.")


if __name__ == "__main__":
    main()
