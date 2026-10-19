# ruff: noqa: E501
"""Add sourced Ooty research tables to the original WildTrack schema.

This migration leaves operational zones, animals and simulation history intact.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_research_evidence"
down_revision: str | None = "0005_historical_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_datasets",
        sa.Column("dataset_key", sa.Text(), primary_key=True),
        sa.Column("doi", sa.Text(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("license_uri", sa.Text(), nullable=False),
        sa.Column("citation", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
    )

    op.create_table(
        "study_regions",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("boundary_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("data_source", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_license", sa.Text(), nullable=False),
        sa.Column("source_version", sa.Text(), nullable=False),
        sa.Column("selection_radius_m", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("geometry", sa.Text(), nullable=False),
        sa.CheckConstraint("selection_radius_m >= 0", name="ck_study_regions_radius_nonnegative"),
    )
    op.execute(
        "alter table public.study_regions alter column geometry type geometry(MultiPolygon,4326) "
        "using ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_GeomFromGeoJSON(geometry)),3))"
    )
    op.create_check_constraint(
        "ck_study_regions_valid_geometry", "study_regions", "not ST_IsEmpty(geometry) and ST_IsValid(geometry)"
    )
    op.create_index("ix_study_regions_geometry", "study_regions", ["geometry"], postgresql_using="gist")

    op.create_table(
        "thematic_zones",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("study_region_code", sa.Text(), sa.ForeignKey("study_regions.code", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("data_source", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_version", sa.Text(), nullable=False),
        sa.Column("source_license", sa.Text(), nullable=False),
        sa.Column("resolution_m", sa.SmallInteger(), nullable=False),
        sa.Column("area_sq_km", sa.Numeric(12, 3), nullable=False),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("geometry", sa.Text(), nullable=False),
        sa.UniqueConstraint("study_region_code", "zone_type", name="uq_thematic_zone_region_type"),
        sa.CheckConstraint(
            "zone_type in ('tree_cover','shrubland','grassland','cultivated_land','built_up','bare_or_sparse_cover','surface_water')",
            name="ck_thematic_zones_supported_class",
        ),
        sa.CheckConstraint("area_sq_km > 0", name="ck_thematic_zones_positive_area"),
        sa.CheckConstraint("resolution_m > 0", name="ck_thematic_zones_positive_resolution"),
    )
    op.execute(
        "alter table public.thematic_zones alter column geometry type geometry(MultiPolygon,4326) "
        "using ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_GeomFromGeoJSON(geometry)),3))"
    )
    op.create_check_constraint(
        "ck_thematic_zones_valid_geometry", "thematic_zones", "not ST_IsEmpty(geometry) and ST_IsValid(geometry)"
    )
    op.create_index("ix_thematic_zones_geometry", "thematic_zones", ["geometry"], postgresql_using="gist")
    op.create_index("ix_thematic_zones_region_type", "thematic_zones", ["study_region_code", "zone_type"])

    op.create_table(
        "wildlife_occurrences",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("source_system", sa.Text(), nullable=False),
        sa.Column("dataset_key", sa.Text(), sa.ForeignKey("research_datasets.dataset_key"), nullable=False),
        sa.Column("source_record_id", sa.Text(), nullable=False),
        sa.Column("source_occurrence_id", sa.Text(), nullable=True),
        sa.Column("species", sa.Text(), nullable=False),
        sa.Column("scientific_name", sa.Text(), nullable=False),
        sa.Column("taxon_id", sa.Text(), nullable=True),
        sa.Column("taxonomic_class", sa.Text(), nullable=True),
        sa.Column("source_observed_at", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("coordinate_uncertainty_m", sa.Numeric(10, 2), nullable=False),
        sa.Column("license_uri", sa.Text(), nullable=False),
        sa.Column("noncommercial_only", sa.Boolean(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("worldcover_class_2021", sa.Text(), nullable=True),
        sa.Column("quality_flags", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("location_uncertainty", sa.Text(), nullable=False),
        sa.UniqueConstraint("source_system", "source_record_id", name="uq_wildlife_occurrences_source_record"),
        sa.CheckConstraint(
            "coordinate_uncertainty_m between 0 and 1000",
            name="ck_occurrences_uncertainty_screen_range",
        ),
        sa.CheckConstraint("length(source_system) > 0", name="ck_occurrences_source_system"),
        sa.CheckConstraint("length(license_uri) > 0", name="ck_occurrences_license_present"),
        sa.CheckConstraint("length(source_url) > 0", name="ck_occurrences_source_url_present"),
    )
    op.execute(
        "alter table public.wildlife_occurrences alter column location type geometry(Point,4326) "
        "using ST_SetSRID(ST_GeomFromText(location),4326)"
    )
    op.execute(
        "alter table public.wildlife_occurrences alter column location_uncertainty "
        "type geometry(Geometry,4326) using ST_SetSRID(ST_GeomFromText(location_uncertainty),4326)"
    )
    op.create_check_constraint(
        "ck_occurrences_valid_location_uncertainty", "wildlife_occurrences",
        "not ST_IsEmpty(location_uncertainty) and ST_IsValid(location_uncertainty)",
    )
    op.create_index("ix_wildlife_occurrences_location", "wildlife_occurrences", ["location"], postgresql_using="gist")
    op.create_index("ix_wildlife_occurrences_observed_at", "wildlife_occurrences", ["observed_at"])
    op.create_index("ix_wildlife_occurrences_species_time", "wildlife_occurrences", ["species", "observed_at"])
    op.create_index("ix_wildlife_occurrences_license", "wildlife_occurrences", ["noncommercial_only", "license_uri"])

    op.create_table(
        "occurrence_region_memberships",
        sa.Column("occurrence_id", sa.BigInteger(), sa.ForeignKey("wildlife_occurrences.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("study_region_code", sa.Text(), sa.ForeignKey("study_regions.code", ondelete="CASCADE"), primary_key=True),
        sa.Column("uncertainty_crosses_boundary", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_occurrence_region_membership_region", "occurrence_region_memberships", ["study_region_code", "uncertainty_crosses_boundary"])


def downgrade() -> None:
    op.drop_index("ix_occurrence_region_membership_region", table_name="occurrence_region_memberships")
    op.drop_table("occurrence_region_memberships")
    for index in (
        "ix_wildlife_occurrences_license",
        "ix_wildlife_occurrences_species_time",
        "ix_wildlife_occurrences_observed_at",
        "ix_wildlife_occurrences_location",
    ):
        op.drop_index(index, table_name="wildlife_occurrences")
    op.drop_table("wildlife_occurrences")
    op.drop_index("ix_thematic_zones_region_type", table_name="thematic_zones")
    op.drop_constraint("ck_thematic_zones_valid_geometry", "thematic_zones", type_="check")
    op.drop_index("ix_thematic_zones_geometry", table_name="thematic_zones")
    op.drop_table("thematic_zones")
    op.drop_index("ix_study_regions_geometry", table_name="study_regions")
    op.drop_constraint("ck_study_regions_valid_geometry", "study_regions", type_="check")
    op.drop_table("study_regions")
    op.drop_table("research_datasets")
