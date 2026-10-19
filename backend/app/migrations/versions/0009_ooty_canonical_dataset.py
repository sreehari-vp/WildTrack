"""Make the sourced Ooty regions and land-cover zones canonical.

The pre-migration database must be backed up before this migration is applied.
Legacy observations, alerts, animals, zones and research footprints are removed
from active tables; the V2 research records and 75 synthetic trackers remain.
"""

from alembic import context, op
import sqlalchemy as sa
import json
from pathlib import Path

revision = "0009_ooty_canonical_dataset"
down_revision = "0008_regional_species_references"
branch_labels = None
depends_on = None

REGION_CODES = (
    "wenlock_downs", "naduvattam", "porthimund", "kundah",
    "mukurthi_lake", "nilgiri_peak", "doddabetta_forest", "kalhatty",
)
REGION_CODES_SQL = ", ".join(f"'{code}'" for code in REGION_CODES)


def upgrade() -> None:
    connection = op.get_bind()
    if not context.is_offline_mode():
        counts = connection.execute(sa.text(f"""
        SELECT
          (SELECT count(*) FROM study_regions WHERE code IN ({REGION_CODES_SQL})) AS regions,
          (SELECT count(*) FROM thematic_zones z JOIN study_regions r ON r.code=z.study_region_code
             WHERE r.code IN ({REGION_CODES_SQL})) AS zones,
          (SELECT count(*) FROM animals WHERE animal_id LIKE 'SIM-V2-%') AS animals
        """)).mappings().one()
        if tuple(counts.values()) != (8, 30, 75):
            raise RuntimeError(f"Ooty V2 precondition failed: {dict(counts)}")

    op.add_column("zones", sa.Column("study_region_code", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_zones_study_region_code", "zones", "study_regions",
        ["study_region_code"], ["code"], ondelete="CASCADE",
    )
    op.drop_constraint("ck_zones_type", "zones", type_="check")

    # Keep only the versioned 75-animal scenario, with a clean history for its
    # new multi-zone routes. Existing records were backed up before this step.
    op.execute("DELETE FROM alerts")
    op.execute("DELETE FROM alert_status_history")
    op.execute("DELETE FROM observations")
    op.execute("DELETE FROM animals WHERE animal_id NOT LIKE 'SIM-V2-%'")
    op.execute("DELETE FROM devices WHERE device_id NOT IN (SELECT device_id FROM animals WHERE device_id IS NOT NULL)")
    op.execute("DELETE FROM event_outbox")
    op.execute("DELETE FROM historical_export_items")
    op.execute("DELETE FROM historical_export_batches")

    # Clear old graph source history and recreate zone version 1 for the Ooty
    # land-cover classes. Zone and rule audit rows describe obsolete scenarios.
    op.execute("DELETE FROM zone_versions")
    op.execute("DELETE FROM eca_rule_versions")
    op.execute("DELETE FROM configuration_audit WHERE entity_type IN ('zones','eca_rules')")
    op.execute("DELETE FROM eca_rules")
    op.execute("DELETE FROM configuration_audit WHERE entity_type = 'eca_rules'")
    op.execute("DELETE FROM zones")
    op.execute("DELETE FROM zone_versions")
    op.execute("DELETE FROM configuration_audit WHERE entity_type = 'zones'")
    op.create_check_constraint(
        "ck_zones_type", "zones",
        "zone_type IN ('tree_cover','grassland','cultivated_land','built_up','bare_or_sparse_cover','surface_water')",
    )

    connection.execute(sa.text(f"""
        INSERT INTO zones
          (zone_id, zone_name, zone_type, risk_level, description, geometry,
           created_in_app, version_no, study_region_code)
        SELECT
          'OTY-' || lpad(row_number() OVER (ORDER BY r.name, z.zone_type)::text, 3, '0'),
          z.name, z.zone_type, 'info',
          concat_ws(' ', z.description,
            'ESA WorldCover land-cover class; hazard and habitat suitability are not assessed.'),
          z.geometry, false, 1, r.code
        FROM thematic_zones z
        JOIN study_regions r ON r.code = z.study_region_code
        WHERE r.code IN ({REGION_CODES_SQL})
        ORDER BY r.name, z.zone_type
    """))

    # Materialize one synthetic starting fix per tracker so all animals are
    # visible on every map immediately after reset, before the first tick.
    manifest_path = Path(__file__).resolve().parents[4] / "data" / "research" / "ooty-v2" / "simulated-mammals.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    starters = []
    for animal in manifest.get("animals", []):
        animal_id = animal["animal_id"]
        longitude, latitude = animal["location"]["coordinates"]
        if not animal_id.startswith("SIM-V2-"):
            raise RuntimeError("Unexpected animal ID in the Ooty simulation manifest")
        starters.append(f"('{animal_id}', {float(longitude):.6f}, {float(latitude):.6f})")
    if len(starters) != 75:
        raise RuntimeError(f"Expected 75 Ooty simulation starting points, got {len(starters)}")
    connection.execute(sa.text(f"""
        INSERT INTO observations
          (observation_id, animal_id, device_id, latitude, longitude, location, speed, observed_at)
        SELECT 'OBS-SIM-BOOT-' || right(a.animal_id, 3), a.animal_id, a.device_id,
               starter.latitude, starter.longitude,
               ST_SetSRID(ST_MakePoint(starter.longitude, starter.latitude), 4326), 0, clock_timestamp()
        FROM animals a
        JOIN (VALUES {', '.join(starters)}) AS starter(animal_id, longitude, latitude)
          ON starter.animal_id = a.animal_id
        WHERE a.device_id IS NOT NULL
    """))

    # The existing zone_version_after trigger creates version 1 per inserted zone.
    op.execute("DELETE FROM configuration_audit WHERE entity_type = 'zones'")

    # Retain source occurrences only when the Ooty V2 package assigned them to
    # one of these eight study extents. Old region rows cascade their memberships.
    connection.execute(sa.text(f"""
        DELETE FROM wildlife_occurrences o
        WHERE NOT EXISTS (
          SELECT 1 FROM occurrence_region_memberships m
          WHERE m.occurrence_id=o.id AND m.study_region_code IN ({REGION_CODES_SQL})
        )
    """))
    connection.execute(sa.text(f"DELETE FROM study_regions WHERE code NOT IN ({REGION_CODES_SQL})"))
    op.execute("""
        DELETE FROM research_datasets d
        WHERE NOT EXISTS (SELECT 1 FROM wildlife_occurrences o WHERE o.dataset_key=d.dataset_key)
    """)

    # The app's shared map boundary is the union of the eight retained extents.
    op.execute("DELETE FROM forest_boundaries")
    op.execute("""
        INSERT INTO forest_boundaries (boundary_id, boundary_name, description, geometry)
        SELECT 'OOTY-ALL', 'Ooty Forest Study Areas',
               'Union of eight source-derived forest analysis extents; not a legal boundary.',
               ST_Multi(ST_Union(geometry))
        FROM study_regions
    """)
    op.execute("""
        DELETE FROM map_pins
        WHERE NOT ST_Covers((SELECT ST_Union(geometry) FROM study_regions), location)
    """)


def downgrade() -> None:
    raise RuntimeError("This data reset is intentionally irreversible; restore the pre-migration pg_dump to roll back.")
