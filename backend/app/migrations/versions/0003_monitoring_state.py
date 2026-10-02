"""Persist officer map work in the existing PostgreSQL database."""

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

revision = "0003_monitoring_state"
down_revision = "0002_integrity"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("zones", sa.Column("created_in_app", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table(
        "map_pins",
        sa.Column("pin_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("pin_type", sa.String(24), nullable=False),
        sa.Column("location", geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("pin_type IN ('Observation','Patrol','Camera','Hazard')", name="ck_map_pins_type"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_map_pins_name"),
    )
    op.create_index("ix_map_pins_location_gist", "map_pins", ["location"], postgresql_using="gist")
    op.create_table(
        "map_preferences",
        sa.Column("preference_id", sa.String(32), primary_key=True),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("map_preferences")
    op.drop_index("ix_map_pins_location_gist", table_name="map_pins")
    op.drop_table("map_pins")
    op.drop_column("zones", "created_in_app")
