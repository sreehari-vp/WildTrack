"""Support regional species checklist provenance for synthetic wildlife."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_regional_species_references"
down_revision: str | None = "0007_simulated_animal_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_animals_data_origin", "animals", type_="check")
    op.create_check_constraint(
        "ck_animals_data_origin", "animals",
        "data_origin in ('legacy_unverified', 'simulated_from_sourced_species', 'simulated_from_regional_species_list')",
    )
    op.add_column("animals", sa.Column("source_reference_type", sa.Text(), nullable=True))
    op.add_column("animals", sa.Column("source_reference_id", sa.Text(), nullable=True))
    op.add_column("animals", sa.Column("source_reference_name", sa.Text(), nullable=True))
    op.add_column("animals", sa.Column("source_reference_url", sa.Text(), nullable=True))
    op.execute("""
        UPDATE animals
        SET source_reference_type = 'gbif_occurrence',
            source_reference_id = source_occurrence_id,
            source_reference_name = 'GBIF occurrence record',
            source_reference_url = source_occurrence_url
        WHERE source_occurrence_id IS NOT NULL OR source_occurrence_url IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column("animals", "source_reference_url")
    op.drop_column("animals", "source_reference_name")
    op.drop_column("animals", "source_reference_id")
    op.drop_column("animals", "source_reference_type")
    op.drop_constraint("ck_animals_data_origin", "animals", type_="check")
    op.create_check_constraint(
        "ck_animals_data_origin", "animals",
        "data_origin in ('legacy_unverified', 'simulated_from_sourced_species')",
    )
