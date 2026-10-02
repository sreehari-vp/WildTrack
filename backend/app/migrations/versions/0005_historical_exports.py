"""Track resumable, incremental Parquet exports for historical processing."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_historical_exports"
down_revision = "0004_history_outbox"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "historical_export_batches",
        sa.Column("batch_id", sa.String(36), primary_key=True),
        sa.Column("dataset", sa.String(24), nullable=False),
        sa.Column("output_root", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("row_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("files", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("hdfs_root", sa.Text()),
        sa.Column("hdfs_published_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("dataset IN ('observations', 'alerts')", name="ck_historical_export_dataset"),
        sa.CheckConstraint("status IN ('preparing', 'ready')", name="ck_historical_export_status"),
        sa.CheckConstraint("row_count >= 0", name="ck_historical_export_count"),
    )
    op.create_index("ix_historical_export_batches_pending", "historical_export_batches", ["dataset", "status", "created_at"])
    op.create_table(
        "historical_export_items",
        sa.Column("dataset", sa.String(24), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("historical_export_batches.batch_id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("dataset", "source_id"),
    )
    op.create_index("ix_historical_export_items_batch", "historical_export_items", ["batch_id"])


def downgrade():
    op.drop_table("historical_export_items")
    op.drop_table("historical_export_batches")
