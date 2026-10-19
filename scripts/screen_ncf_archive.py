"""Screen the NCF/GBIF Darwin Core archive against finalized study-region geometry."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

from shapely.geometry import Point, shape

ARCHIVE = Path("data/raw/dwca-anam-mammals-2023-26-v1.0.zip")
REGIONS = Path("data/research/phase1-study-regions.geojson")
OUTPUT = Path("data/research/ncf-phase1-candidate-records.json")
DOI = "10.15468/yv8qss"


def main() -> None:
    region_features = json.loads(REGIONS.read_text(encoding="utf-8"))["features"]
    region_geometries = {feature["properties"]["code"]: shape(feature["geometry"]) for feature in region_features}
    with zipfile.ZipFile(ARCHIVE) as archive:
        with archive.open("occurrence.txt") as member:
            reader = csv.DictReader(io.TextIOWrapper(member, encoding="utf-8-sig"), delimiter="\t")
            rows = list(reader)

    selected = []
    rejected = Counter()
    for row in rows:
        try:
            lat = float(row["decimalLatitude"])
            lon = float(row["decimalLongitude"])
            uncertainty = float(row["coordinateUncertaintyInMeters"])
        except (TypeError, ValueError):
            rejected["missing_or_invalid_coordinates_or_uncertainty"] += 1
            continue
        if not row.get("eventDate") or not row.get("occurrenceID"):
            rejected["missing_date_or_source_record_id"] += 1
            continue
        licence = row.get("license", "").strip().lower()
        if not (
            licence.endswith("creativecommons.org/licenses/by/4.0/legalcode")
            or licence in {"cc-by-4.0", "cc by 4.0", "cc0-1.0", "cc0"}
        ):
            rejected["unsupported_or_missing_record_licence"] += 1
            continue
        if uncertainty > 1000:
            rejected["coordinate_uncertainty_over_1km"] += 1
            continue
        point = Point(lon, lat)
        memberships = [code for code, geometry in region_geometries.items() if geometry.covers(point)]
        if not memberships:
            rejected["outside_study_region_geometry"] += 1
            continue
        selected.append({
            "source": "Nature Conservation Foundation via GBIF",
            "source_id": row["occurrenceID"],
            "gbif_key": row.get("id"),
            "dataset_doi": DOI,
            "source_url": f"https://www.gbif.org/occurrence/{row.get('id')}" if row.get("id") else None,
            "species": row.get("scientificName"),
            "class": row.get("class"),
            "event_date": row.get("eventDate"),
            "latitude": lat,
            "longitude": lon,
            "coordinate_uncertainty_m": uncertainty,
            "basis_of_record": row.get("basisOfRecord"),
            "locality": row.get("verbatimLocality"),
            "field_notes": row.get("fieldNotes"),
            "licence": row.get("license"),
            "region_codes": memberships,
            "candidate_only": True,
        })

    unique = {record["source_id"]: record for record in selected}
    OUTPUT.write_text(json.dumps(list(unique.values()), indent=2) + "\n", encoding="utf-8")
    report = {
        "source": "Nature Conservation Foundation, Occurrence records of mammals from the Western Ghats (primarily Sakleshpur, Anamalais and Nilgiris, India) between November 2023 and February 2026",
        "dataset_doi": DOI,
        "licence": "CC BY 4.0",
        "archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        "input_rows": len(rows),
        "unique_candidate_records_inside_regions": len(unique),
        "by_species": dict(Counter(record["species"] for record in unique.values())),
        "by_region_membership": dict(Counter(code for record in unique.values() for code in record["region_codes"])),
        "rejected": dict(rejected),
        "output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "limitation": "Candidates are reported observations, not live or tagged animal telemetry. HumanObservation records may describe direct sightings or animal signs; inspect field notes and source context before display.",
    }
    Path("data/research/ncf-phase1-screen-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"input_rows": len(rows), "candidate_count": len(unique), "species": report["by_species"], "region_counts": report["by_region_membership"], "rejected": report["rejected"]}, indent=2))


if __name__ == "__main__":
    main()
