# ruff: noqa: E501
"""Idempotently import the Phase 1 regions, WorldCover zones and GBIF events.

Dry-run is the default. Pass --apply only after applying Alembic revision
20261018_0008 to the intended PostgreSQL/PostGIS database.
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

REGIONS_PATH = ROOT / "data/research/phase1-study-regions.geojson"
ZONES_PATH = ROOT / "data/research/phase2-landcover-zones.geojson"
OCCURRENCES_PATH = ROOT / "data/research/phase1-observation-candidates.json"
DATASETS_PATH = ROOT / "data/research/gbif-dataset-metadata.json"
FOREST_METADATA_PATH = ROOT / "data/research/nilgiris-soi-forest-features.json"
MUKURTHI_METADATA_PATH = ROOT / "data/research/mukurthi-national-park-gatishakti.json"
DATASET_URL = "https://api.gbif.org/v1/dataset/{}"


def read_inputs() -> tuple[list[dict], list[dict], list[dict], dict[str, dict]]:
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))["features"]
    zones = json.loads(ZONES_PATH.read_text(encoding="utf-8"))["features"]
    occurrences = json.loads(OCCURRENCES_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(DATASETS_PATH.read_text(encoding="utf-8"))["datasets"]
    used_keys = {row["dataset_key"] for row in occurrences}
    datasets = {item["key"]: item for item in metadata if item.get("key") in used_keys}
    missing = used_keys - datasets.keys()
    if missing:
        raise ValueError(f"Missing GBIF dataset metadata for keys: {sorted(missing)}")
    for row in occurrences:
        if not row.get("region_codes"):
            raise ValueError(f"Occurrence {row.get('source_id')} has no study-region membership")
        if not row.get("licence") or not row.get("source_url"):
            raise ValueError(f"Occurrence {row.get('source_id')} is missing its source/licence")
    return regions, zones, occurrences, datasets


def dataset_values(key: str, item: dict) -> dict:
    citation = item.get("citation") or {}
    return {
        "dataset_key": key,
        "doi": item.get("doi") or f"GBIF:{key}",
        "title": item.get("title") or "Untitled GBIF occurrence dataset",
        "license_uri": item.get("license") or "https://gbif.org",
        "citation": citation.get("text") or item.get("title") or f"GBIF dataset {key}",
        "source_url": DATASET_URL.format(key),
        "publisher": item.get("publishingOrganizationTitle"),
        "accessed_at": datetime.now(UTC),
        "source_metadata": json.dumps({"type": item.get("type"), "pubDate": item.get("pubDate")}),
    }


def upsert_dataset(connection, values: dict) -> None:
    connection.execute(text("""
        insert into public.research_datasets
          (dataset_key, doi, title, license_uri, citation, source_url, publisher, accessed_at, source_metadata)
        values
          (:dataset_key, :doi, :title, :license_uri, :citation, :source_url, :publisher, :accessed_at,
           cast(:source_metadata as jsonb))
        on conflict (dataset_key) do update set
          doi = excluded.doi, title = excluded.title, license_uri = excluded.license_uri,
          citation = excluded.citation, source_url = excluded.source_url, publisher = excluded.publisher,
          accessed_at = excluded.accessed_at, source_metadata = excluded.source_metadata
    """), values)


def upsert_region(connection, feature: dict) -> None:
    props = feature["properties"]
    source_doc = json.loads((MUKURTHI_METADATA_PATH if props["code"] == "mukurthi" else FOREST_METADATA_PATH).read_text(encoding="utf-8"))
    source_version = "PM GatiShakti 2024 snapshot" if props["code"] == "mukurthi" else "Survey of India forest extract, accessed 2026-10-17"
    values = {
        "code": props["code"], "name": props["name"], "boundary_type": props["boundary_type"],
        "description": props["boundary_type"], "data_source": props["data_source"],
        "source_url": source_doc["source_url"], "source_license": source_doc["licence"],
        "source_version": source_version,
        "selection_radius_m": props["selection_radius_m"],
        "source_metadata": json.dumps({"source_features": props["source_features"], "publisher": source_doc.get("publisher"),
            "source_sha256": source_doc.get("source_sha256")}),
        "geometry": json.dumps(feature["geometry"], separators=(",", ":")),
    }
    connection.execute(text("""
        insert into public.study_regions
          (code, name, boundary_type, description, data_source, source_url, source_license, source_version,
           selection_radius_m, source_metadata, geometry)
        values (:code, :name, :boundary_type, :description, :data_source, :source_url, :source_license,
          :source_version, :selection_radius_m, cast(:source_metadata as jsonb),
          ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326)), 3)))
        on conflict (code) do update set
          name = excluded.name, boundary_type = excluded.boundary_type, description = excluded.description,
          data_source = excluded.data_source, source_url = excluded.source_url,
          source_license = excluded.source_license,
          source_version = excluded.source_version, selection_radius_m = excluded.selection_radius_m,
          source_metadata = excluded.source_metadata, geometry = excluded.geometry
    """), values)


def upsert_zone(connection, feature: dict) -> None:
    props = feature["properties"]
    values = {
        "code": props["code"], "study_region_code": props["region_code"],
        "zone_type": props["zone_type"], "name": props["name"], "description": props["description"],
        "data_source": props["data_source"], "source_url": props["source_url"],
        "source_version": "ESA WorldCover 10 m 2021 v200", "source_license": props["source_license"],
        "resolution_m": props["resolution_m"], "area_sq_km": props["area_sq_km"],
        "source_metadata": json.dumps({key: props[key] for key in (
            "source_doi", "minimum_component_area_m2", "simplification_tolerance_degrees", "legal_status"
        )}),
        "geometry": json.dumps(feature["geometry"], separators=(",", ":")),
    }
    connection.execute(text("""
        insert into public.thematic_zones
          (code, study_region_code, zone_type, name, description, data_source, source_url,
           source_version, source_license, resolution_m, area_sq_km, source_metadata, geometry)
        values (:code, :study_region_code, :zone_type, :name, :description, :data_source,
          :source_url, :source_version, :source_license, :resolution_m, :area_sq_km,
          cast(:source_metadata as jsonb),
          ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326)), 3)))
        on conflict (code) do update set
          study_region_code = excluded.study_region_code, zone_type = excluded.zone_type,
          name = excluded.name, description = excluded.description, data_source = excluded.data_source,
          source_url = excluded.source_url, source_version = excluded.source_version,
          source_license = excluded.source_license, resolution_m = excluded.resolution_m,
          area_sq_km = excluded.area_sq_km, source_metadata = excluded.source_metadata,
          geometry = excluded.geometry
    """), values)


def upsert_occurrence(connection, row: dict) -> int:
    source_event_date = str(row["observed_on"])
    observed_at = datetime.fromisoformat(source_event_date.replace("Z", "+00:00"))
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    values = {
        "source_system": "GBIF", "dataset_key": row["dataset_key"],
        "source_record_id": str(row["source_id"]), "source_occurrence_id": row.get("original_occurrence_id"),
        "species": row["species"], "scientific_name": row["species"],
        "taxon_id": str(row["taxon_id"]) if row.get("taxon_id") is not None else None,
        "taxonomic_class": row.get("class"), "source_observed_at": source_event_date,
        "observed_at": observed_at,
        "coordinate_uncertainty_m": row["positional_accuracy_m"], "license_uri": row["licence"],
        "noncommercial_only": row["noncommercial_only"], "source_url": row["source_url"],
        "worldcover_class_2021": row.get("worldcover_class_2021_at_reported_point"),
        "quality_flags": ["boundary_uncertainty_crosses_edge"] if row["boundary_membership_uncertain"] else [],
        "source_metadata": json.dumps({"candidate_only": True, "dataset_title": row.get("dataset_title"),
            "dataset_doi": row.get("dataset_doi"), "dataset_citation": row.get("dataset_citation")}),
        "longitude": row["longitude"], "latitude": row["latitude"],
    }
    result = connection.execute(text("""
        insert into public.wildlife_occurrences
          (source_system, dataset_key, source_record_id, source_occurrence_id, species, scientific_name,
           taxon_id, taxonomic_class, source_observed_at, observed_at, coordinate_uncertainty_m, license_uri,
           noncommercial_only, source_url, worldcover_class_2021, quality_flags, source_metadata,
           location, location_uncertainty)
        values
          (:source_system, :dataset_key, :source_record_id, :source_occurrence_id, :species, :scientific_name,
           :taxon_id, :taxonomic_class, :source_observed_at, :observed_at, :coordinate_uncertainty_m,
           :license_uri, :noncommercial_only, :source_url, :worldcover_class_2021, :quality_flags,
           cast(:source_metadata as jsonb),
           ST_SetSRID(ST_MakePoint(:longitude, :latitude),4326),
           ST_Buffer(ST_SetSRID(ST_MakePoint(:longitude, :latitude),4326)::geography,
             greatest(:coordinate_uncertainty_m, 1))::geometry)
        on conflict (source_system, source_record_id) do update set
          dataset_key = excluded.dataset_key, source_occurrence_id = excluded.source_occurrence_id,
          species = excluded.species, scientific_name = excluded.scientific_name,
          taxon_id = excluded.taxon_id, taxonomic_class = excluded.taxonomic_class,
          source_observed_at = excluded.source_observed_at, observed_at = excluded.observed_at,
          coordinate_uncertainty_m = excluded.coordinate_uncertainty_m,
          license_uri = excluded.license_uri, noncommercial_only = excluded.noncommercial_only,
          source_url = excluded.source_url, worldcover_class_2021 = excluded.worldcover_class_2021,
          quality_flags = excluded.quality_flags, source_metadata = excluded.source_metadata,
          location = excluded.location, location_uncertainty = excluded.location_uncertainty
        returning id
    """), values)
    occurrence_id = int(result.scalar_one())
    connection.execute(text("delete from public.occurrence_region_memberships where occurrence_id = :id"), {"id": occurrence_id})
    for region_code in row["region_codes"]:
        connection.execute(text("""
            insert into public.occurrence_region_memberships
              (occurrence_id, study_region_code, uncertainty_crosses_boundary)
            values (:occurrence_id, :region_code, :uncertain)
        """), {"occurrence_id": occurrence_id, "region_code": region_code,
            "uncertain": row["boundary_membership_uncertain"]})
    return occurrence_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the rows to DATABASE_URL; default only validates and reports")
    args = parser.parse_args()
    regions, zones, occurrences, datasets = read_inputs()
    summary = {
        "study_regions": len(regions), "thematic_zones": len(zones),
        "datasets": len(datasets), "observation_candidates": len(occurrences),
        "unique_species": len({row["species"] for row in occurrences}),
        "noncommercial_records": sum(bool(row["noncommercial_only"]) for row in occurrences),
        "mode": "apply" if args.apply else "dry-run",
    }
    if not args.apply:
        print(json.dumps(summary, indent=2))
        return
    settings = get_settings()
    if not settings.sqlalchemy_database_url:
        raise SystemExit("DATABASE_URL is not configured. No data was imported.")
    engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True, connect_args={"prepare_threshold": None})
    try:
        with engine.begin() as connection:
            for key, item in datasets.items():
                upsert_dataset(connection, dataset_values(key, item))
            for feature in regions:
                upsert_region(connection, feature)
            for feature in zones:
                upsert_zone(connection, feature)
            inserted_ids = [upsert_occurrence(connection, row) for row in occurrences]
            summary["database_occurrence_ids"] = len(inserted_ids)
        print(json.dumps(summary, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
