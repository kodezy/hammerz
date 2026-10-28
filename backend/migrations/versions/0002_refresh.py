"""refresh tokens

Revision ID: 0002_refresh
Revises: 0001_init
Create Date: 2026-10-28
"""

from alembic import op
from sqlalchemy import inspect

revision = "0002_refresh"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("refresh_tokens"):
        return
    from src.db.tables import Base

    RefreshToken = Base.metadata.tables["refresh_tokens"]
    RefreshToken.create(bind, checkfirst=True)


def downgrade() -> None:
    op.drop_table("refresh_tokens")
