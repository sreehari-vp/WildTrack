"""database foundation

Revision ID: 0001_database_foundation
Revises:
Create Date: 2026-09-24
"""
from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_database_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "devices",
        sa.Column("device_id", sa.String(length=32), primary_key=True),
        sa.Column("device_code", sa.String(length=32), nullable=False),
        sa.Column("device_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("battery_level", sa.Integer(), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("battery_level BETWEEN 0 AND 100", name="ck_devices_battery_level"),
        sa.UniqueConstraint("device_code", name="uq_devices_device_code"),
    )

    op.create_table(
        "animals",
        sa.Column("animal_id", sa.String(length=32), primary_key=True),
        sa.Column("animal_code", sa.String(length=32), nullable=False),
        sa.Column("species", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("device_id", sa.String(length=32), sa.ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("animal_code", name="uq_animals_animal_code"),
        sa.UniqueConstraint("device_id", name="uq_animals_device_id"),
    )
    op.create_index("ix_animals_species", "animals", ["species"])
    op.create_index("ix_animals_status", "animals", ["status"])

    op.create_table(
        "forest_boundaries",
        sa.Column("boundary_id", sa.String(length=32), primary_key=True),
        sa.Column("boundary_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("boundary_name", name="uq_forest_boundaries_boundary_name"),
    )
    op.create_index("ix_forest_boundaries_geometry_gist", "forest_boundaries", ["geometry"], postgresql_using="gist")

    op.create_table(
        "zones",
        sa.Column("zone_id", sa.String(length=32), primary_key=True),
        sa.Column("zone_name", sa.String(length=120), nullable=False),
        sa.Column("zone_type", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=24), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("zone_name", name="uq_zones_zone_name"),
    )
    op.create_index("ix_zones_zone_type", "zones", ["zone_type"])
    op.create_index("ix_zones_risk_level", "zones", ["risk_level"])
    op.create_index("ix_zones_geometry_gist", "zones", ["geometry"], postgresql_using="gist")

    op.create_table(
        "observations",
        sa.Column("observation_id", sa.String(length=32), primary_key=True),
        sa.Column("animal_id", sa.String(length=32), sa.ForeignKey("animals.animal_id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(length=32), sa.ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("location", geoalchemy2.Geometry("POINT", srid=4326), nullable=False),
        sa.Column("speed", sa.Numeric(6, 2), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_observations_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_observations_longitude"),
    )
    op.create_index("ix_observations_animal_observed_at", "observations", ["animal_id", "observed_at"])
    op.create_index("ix_observations_device_observed_at", "observations", ["device_id", "observed_at"])
    op.create_index("ix_observations_observed_at", "observations", ["observed_at"])
    op.create_index("ix_observations_location_gist", "observations", ["location"], postgresql_using="gist")

    op.create_table(
        "eca_rules",
        sa.Column("rule_id", sa.String(length=32), primary_key=True),
        sa.Column("rule_name", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("condition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("rule_name", name="uq_eca_rules_rule_name"),
    )
    op.create_index("ix_eca_rules_event_type", "eca_rules", ["event_type"])
    op.create_index("ix_eca_rules_enabled", "eca_rules", ["enabled"])

    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.String(length=32), primary_key=True),
        sa.Column("animal_id", sa.String(length=32), sa.ForeignKey("animals.animal_id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", sa.String(length=32), sa.ForeignKey("zones.zone_id", ondelete="SET NULL"), nullable=True),
        sa.Column("rule_id", sa.String(length=32), sa.ForeignKey("eca_rules.rule_id", ondelete="SET NULL"), nullable=True),
        sa.Column("alert_type", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alerts_animal_id", "alerts", ["animal_id"])
    op.create_index("ix_alerts_zone_id", "alerts", ["zone_id"])
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"])
    op.create_index("ix_alerts_status_severity", "alerts", ["status", "severity"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("eca_rules")
    op.drop_table("observations")
    op.drop_table("zones")
    op.drop_table("forest_boundaries")
    op.drop_table("animals")
    op.drop_table("devices")
