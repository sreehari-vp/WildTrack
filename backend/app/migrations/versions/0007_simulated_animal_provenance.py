"""Track simulation provenance separately from sourced field occurrences."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_simulated_animal_provenance"
down_revision: str | None = "0006_research_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("animals", sa.Column("data_origin", sa.Text(), nullable=False, server_default="legacy_unverified"))
    op.add_column("animals", sa.Column("source_occurrence_id", sa.Text(), nullable=True))
    op.add_column("animals", sa.Column("source_occurrence_url", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_animals_data_origin",
        "animals",
        "data_origin in ('legacy_unverified', 'simulated_from_sourced_species')",
    )
    op.create_index("ix_animals_data_origin", "animals", ["data_origin"])


def downgrade() -> None:
    op.drop_index("ix_animals_data_origin", table_name="animals")
    op.drop_constraint("ck_animals_data_origin", "animals", type_="check")
    op.drop_column("animals", "source_occurrence_url")
    op.drop_column("animals", "source_occurrence_id")
    op.drop_column("animals", "data_origin")
