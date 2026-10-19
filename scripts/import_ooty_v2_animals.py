"""Add the versioned 75-mammal simulation to the original Desktop schema.

Existing animal/device/observation rows are never deleted. Dry-run is default.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generate_simulated_population import apply_population  # noqa: E402

DIRECTORY = ROOT / "data/research/ooty-v2"
CATALOG = DIRECTORY / "mammal-species-catalog.json"


def build_manifest() -> dict:
    source = json.loads((DIRECTORY / "simulated-mammals.json").read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    by_species = {item["scientific_name"]: item for item in catalog["species"]}
    records = []
    routes = {}
    for item in source["animals"]:
        species = by_species.get(item["scientific_name"])
        if species is None:
            raise ValueError(f"Missing species source: {item['scientific_name']}")
        source_by_id = {"tnau_mukurthi": catalog["sources"][0], "sumithran_1997": catalog["sources"][1]}
        source = source_by_id[species["source_ids"][0]]
        animal_id = item["animal_id"]
        if not animal_id.startswith("SIM-V2-"):
            raise ValueError("V2 animal ID prefix missing")
        longitude, latitude = item["location"]["coordinates"]
        records.append({
            "animal_id": animal_id,
            "animal_code": animal_id,
            "species": item["scientific_name"],
            "name": f"{item['common_name']} {animal_id[-3:]}",
            "device_id": f"SIM-V2-DEV-{animal_id[-3:]}",
            "source_reference_id": f"ooty-v2:{species['scientific_name']}",
            "source_reference_name": source["name"],
            "source_reference_url": source["url"],
            "initial_location": {"longitude": longitude, "latitude": latitude},
        })
        routes[animal_id] = [[point["longitude"], point["latitude"]] for point in item["route"]]
    counts = Counter(item["species"] for item in records)
    if len(records) != 75 or len(counts) != 16:
        raise ValueError("Expected 75 synthetic mammals across 16 species")
    return {"animal_records": records, "routes": routes, "species_distribution": counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-file", type=Path, help="existing pg_dump required for --apply")
    args = parser.parse_args()
    manifest = build_manifest()
    print(json.dumps({"animals": len(manifest["animal_records"]), "species": len(manifest["species_distribution"]),
                      "elephants": manifest["species_distribution"]["Elephas maximus"],
                      "mode": "apply" if args.apply else "dry-run"}, indent=2))
    if not args.apply:
        return
    if not args.backup_file or not args.backup_file.is_file() or args.backup_file.stat().st_size < 100_000:
        parser.error("--apply requires an existing nonempty --backup-file")
    inserted = apply_population(manifest)
    print(f"Upserted {inserted} versioned synthetic mammal trackers; previous rows were retained")


if __name__ == "__main__":
    main()
