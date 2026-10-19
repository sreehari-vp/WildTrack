"""Check that the Phase 2 source package was imported intact.

Read-only. Exit nonzero when a source record, zone, region, membership or
licence flag disagrees with the files in data/research.
"""

from __future__ import annotations

import json

from sqlalchemy import create_engine, text

from import_ooty_research_data import get_settings, read_inputs

def main() -> None:
    regions, zones, occurrences, datasets = read_inputs()
    settings = get_settings()
    if not settings.sqlalchemy_database_url:
        raise SystemExit("DATABASE_URL is not configured.")

    engine = create_engine(
        settings.sqlalchemy_database_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )
    try:
        with engine.connect() as connection:
            db_regions = set(connection.execute(text("select code from public.study_regions")).scalars())
            db_zones = set(connection.execute(text("select code from public.thematic_zones")).scalars())
            db_datasets = set(connection.execute(text("select dataset_key from public.research_datasets")).scalars())
            db_occurrences = {
                str(row.source_record_id): row
                for row in connection.execute(text("""
                    select source_record_id, species, dataset_key, license_uri, noncommercial_only
                    from public.wildlife_occurrences where source_system = 'GBIF'
                """))
            }
            db_memberships = {
                (str(row.source_record_id), row.study_region_code, row.uncertainty_crosses_boundary)
                for row in connection.execute(text("""
                    select o.source_record_id, m.study_region_code, m.uncertainty_crosses_boundary
                    from public.occurrence_region_memberships m
                    join public.wildlife_occurrences o on o.id = m.occurrence_id
                    where o.source_system = 'GBIF'
                """))
            }
            invalid_geometries = int(connection.execute(text("""
                select
                  (select count(*) from public.study_regions where not ST_IsValid(geometry)) +
                  (select count(*) from public.thematic_zones where not ST_IsValid(geometry)) +
                  (select count(*) from public.wildlife_occurrences
                    where not ST_IsValid(location) or not ST_IsValid(location_uncertainty))
            """)).scalar_one())

        expected_regions = {feature["properties"]["code"] for feature in regions}
        expected_zones = {feature["properties"]["code"] for feature in zones}
        expected_occurrences = {str(row["source_id"]): row for row in occurrences}
        expected_memberships = {
            (str(row["source_id"]), code, bool(row["boundary_membership_uncertain"]))
            for row in occurrences for code in row["region_codes"]
        }
        mismatched_records = sorted(source_id for source_id, source in expected_occurrences.items()
            if source_id in db_occurrences and (
                db_occurrences[source_id].species != source["species"]
                or db_occurrences[source_id].dataset_key != source["dataset_key"]
                or db_occurrences[source_id].license_uri != source["licence"]
                or db_occurrences[source_id].noncommercial_only != bool(source["noncommercial_only"])
            ))
        checks = {
            "regions_present": expected_regions <= db_regions,
            "zones_present": expected_zones <= db_zones,
            "datasets_present": set(datasets) <= db_datasets,
            "source_records_present": set(expected_occurrences) <= db_occurrences.keys(),
            "source_record_fields_match": not mismatched_records,
            "region_memberships_present": expected_memberships <= db_memberships,
            "invalid_geometries": invalid_geometries == 0,
        }
        report = {
            "checks": checks,
            "expected": {
                "regions": len(expected_regions), "zones": len(expected_zones),
                "datasets": len(datasets), "source_records": len(expected_occurrences),
                "region_memberships": len(expected_memberships),
            },
            "missing": {
                "regions": sorted(expected_regions - db_regions),
                "zones": sorted(expected_zones - db_zones),
                "datasets": sorted(set(datasets) - db_datasets),
                "source_records": sorted(set(expected_occurrences) - db_occurrences.keys()),
                "region_memberships": len(expected_memberships - db_memberships),
                "mismatched_records": mismatched_records,
            },
            "invalid_geometry_count": invalid_geometries,
        }
        print(json.dumps(report, indent=2))
        if not all(checks.values()):
            raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
