"""Screen the fresh GBIF snapshot against V2 forest and land-cover polygons."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from shapely.geometry import Point, shape

from finalize_phase1_dataset import valid_candidate

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/research/ooty-v2"
EXCLUDED_DOMESTIC = {"Bubalus bubalis", "Felis catus", "Canis familiaris", "Bos taurus"}
# Mortality events are useful evidence, but should not be shown as live-wildlife
# sightings or used to seed moving animals.
EXCLUDED_DATASETS = {"d3b6cb30-0a64-4f82-91ea-0bb14637ee17"}


def main() -> None:
    source = json.loads((DIRECTORY / "gbif-mammal-search.json").read_text(encoding="utf-8"))
    regions = json.loads((DIRECTORY / "study-regions.geojson").read_text(encoding="utf-8"))["features"]
    zones = json.loads((DIRECTORY / "landcover-zones.geojson").read_text(encoding="utf-8"))["features"]
    region_shapes = [(item["properties"]["code"], shape(item["geometry"])) for item in regions]
    zone_shapes = [(item["properties"]["code"], shape(item["geometry"])) for item in zones]
    accepted = []
    excluded = Counter()
    seen_ids = set()
    for record in source["records"]:
        source_id = record.get("key")
        if source_id in seen_ids:
            excluded["duplicate_key"] += 1
            continue
        seen_ids.add(source_id)
        if not valid_candidate(record):
            excluded["quality_or_licence"] += 1
            continue
        if record.get("datasetKey") in EXCLUDED_DATASETS:
            excluded["roadkill_dataset"] += 1
            continue
        species = record.get("species") or record.get("scientificName")
        if species in EXCLUDED_DOMESTIC:
            excluded["domestic_species"] += 1
            continue
        point = Point(float(record["decimalLongitude"]), float(record["decimalLatitude"]))
        memberships = [code for code, geom in region_shapes if geom.covers(point)]
        if not memberships:
            excluded["outside_selected_forests"] += 1
            continue
        zone_memberships = [code for code, geom in zone_shapes if geom.covers(point)]
        accepted.append({
            "source_system": "GBIF",
            "source_id": source_id,
            "source_url": f"https://www.gbif.org/occurrence/{source_id}",
            "dataset_key": record.get("datasetKey"),
            "original_occurrence_id": record.get("occurrenceID"),
            "species": species,
            "common_name": record.get("vernacularName"),
            "observed_on": record["eventDate"],
            "longitude": point.x,
            "latitude": point.y,
            "coordinate_uncertainty_m": float(record["coordinateUncertaintyInMeters"]),
            "licence": record["license"],
            "region_codes": memberships,
            "zone_codes": zone_memberships,
            "data_origin": "historical_public_observation_candidate",
            "candidate_only": True,
        })
    accepted.sort(key=lambda row: (row["observed_on"], row["source_id"]))
    report = {
        "downloaded": len(source["records"]),
        "accepted_candidates": len(accepted),
        "distinct_species": len({row["species"] for row in accepted}),
        "per_region": dict(sorted(Counter(code for row in accepted for code in row["region_codes"]).items())),
        "per_species": dict(sorted(Counter(row["species"] for row in accepted).items())),
        "excluded": dict(sorted(excluded.items())),
        "limitations": [
            "Records are historical candidate observations, not tracked individual animals.",
            "Forest coverage is uneven; no artificial sightings are added to empty regions.",
            "Reported coordinates carry uncertainty and are not guaranteed exact animal positions.",
        ],
    }
    (DIRECTORY / "mammal-observation-candidates.json").write_text(json.dumps(accepted, indent=2) + "\n", encoding="utf-8")
    (DIRECTORY / "mammal-screen-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
