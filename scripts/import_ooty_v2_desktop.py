"""Add Ooty V2 research evidence to the original Desktop WildTrack database.

This does not delete or rewrite the original six regions, zones, sightings,
animals, or simulation history. Dry-run is the default.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.core.config import get_settings  # noqa: E402
from import_ooty_research_data import (  # noqa: E402
    dataset_values, upsert_dataset, upsert_region, upsert_zone,
)

DIRECTORY = ROOT / "data/research/ooty-v2"


def load_inputs() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    regions = json.loads((DIRECTORY / "study-regions.geojson").read_text(encoding="utf-8"))["features"]
    zones = json.loads((DIRECTORY / "landcover-zones.geojson").read_text(encoding="utf-8"))["features"]
    occurrences = json.loads((DIRECTORY / "mammal-observation-candidates.json").read_text(encoding="utf-8"))
    datasets = json.loads((DIRECTORY / "gbif-datasets.json").read_text(encoding="utf-8"))["datasets"]
    region_codes = {feature["properties"]["code"] for feature in regions}
    if len(regions) != 8 or len(zones) != 30 or len(occurrences) != 35:
        raise ValueError("V2 package counts differ from the screened release")
    if any(zone["properties"]["region_code"] not in region_codes for zone in zones):
        raise ValueError("A zone has no V2 parent region")
    if any(set(row["region_codes"]) - region_codes for row in occurrences):
        raise ValueError("A sighting has a non-V2 region membership")
    if {row["dataset_key"] for row in occurrences} - {item["key"] for item in datasets}:
        raise ValueError("A GBIF dataset attribution record is missing")
    return regions, zones, occurrences, datasets


def insert_occurrence(connection, row: dict) -> None:
    observed_at = datetime.fromisoformat(str(row["observed_on"]).replace("Z", "+00:00"))
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    values = {
        "source_record_id": str(row["source_id"]),
        "source_occurrence_id": row.get("original_occurrence_id"),
        "dataset_key": row["dataset_key"],
        "species": row["species"],
        "observed_text": row["observed_on"],
        "observed_at": observed_at,
        "uncertainty": row["coordinate_uncertainty_m"],
        "licence": row["licence"],
        "noncommercial": "/by-nc/" in str(row["licence"]).lower(),
        "source_url": row["source_url"],
        "longitude": row["longitude"],
        "latitude": row["latitude"],
        "source_metadata": json.dumps({"candidate_only": True, "dataset_version": "ooty-v2"}),
    }
    occurrence_id = connection.execute(text("""
        insert into public.wildlife_occurrences
          (source_system, dataset_key, source_record_id, source_occurrence_id,
           species, scientific_name, taxonomic_class, source_observed_at,
           observed_at, coordinate_uncertainty_m, license_uri,
           noncommercial_only, source_url, source_metadata, location,
           location_uncertainty)
        values
          ('GBIF', :dataset_key, :source_record_id, :source_occurrence_id,
           :species, :species, 'Mammalia', :observed_text,
           :observed_at, :uncertainty, :licence,
           :noncommercial, :source_url, cast(:source_metadata as jsonb),
           ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
           ST_Buffer(ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
             greatest(:uncertainty, 1))::geometry)
        on conflict (source_system, source_record_id) do nothing
        returning id
    """), values).scalar_one_or_none()
    if occurrence_id is None:
        occurrence_id = connection.execute(text("""
            select id from public.wildlife_occurrences
            where source_system = 'GBIF' and source_record_id = :source_record_id
        """), values).scalar_one()
    for region_code in row["region_codes"]:
        connection.execute(text("""
            insert into public.occurrence_region_memberships
              (occurrence_id, study_region_code, uncertainty_crosses_boundary)
            select :occurrence_id, r.code,
              not ST_Covers(r.geometry,
                ST_Buffer(o.location::geography, greatest(o.coordinate_uncertainty_m, 1))::geometry)
            from public.study_regions r
            join public.wildlife_occurrences o on o.id = :occurrence_id
            where r.code = :region_code
            on conflict (occurrence_id, study_region_code) do nothing
        """), {"occurrence_id": occurrence_id, "region_code": region_code})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-file", type=Path, help="existing pg_dump required for --apply")
    args = parser.parse_args()
    regions, zones, occurrences, datasets = load_inputs()
    summary = {"regions": len(regions), "zones": len(zones), "sightings": len(occurrences),
               "species": len({row["species"] for row in occurrences}), "mode": "apply" if args.apply else "dry-run"}
    if not args.apply:
        print(json.dumps(summary, indent=2))
        return
    if not args.backup_file or not args.backup_file.is_file() or args.backup_file.stat().st_size < 100_000:
        parser.error("--apply requires an existing nonempty --backup-file")
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True, connect_args={"prepare_threshold": None})
    try:
        with engine.begin() as connection:
            for item in datasets:
                upsert_dataset(connection, dataset_values(item["key"], item))
            for feature in regions:
                props = feature["properties"]
                props["selection_radius_m"] = 0
                props["source_features"] = [{"name": props["source_name"], "count": props["source_feature_count"]}]
                upsert_region(connection, feature)
            for feature in zones:
                upsert_zone(connection, feature)
            for row in occurrences:
                insert_occurrence(connection, row)
        print(json.dumps(summary, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
