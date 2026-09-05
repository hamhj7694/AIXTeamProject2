"""001: V4 ownership marker; business entities follow in Phase 1."""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_metadata",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", sa.String(200), nullable=False),
    )
    marker = sa.table("application_metadata", sa.column("key", sa.String), sa.column("value", sa.String))
    op.bulk_insert(marker, [{"key": "application", "value": "csr_v4"}])


def downgrade() -> None:
    op.drop_table("application_metadata")
