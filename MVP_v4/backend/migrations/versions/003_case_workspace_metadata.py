"""003: additive user-facing Case metadata and reversible trash."""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cases", sa.Column("title", sa.String(200), nullable=False, server_default=""))
    op.add_column("cases", sa.Column("summary", sa.String(1000), nullable=False, server_default=""))
    op.add_column("cases", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cases", sa.Column("deleted_by", sa.String(128), nullable=True))


def downgrade():
    for name in ("deleted_by", "deleted_at", "summary", "title"):
        op.drop_column("cases", name)
