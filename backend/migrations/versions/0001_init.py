"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-10-26
"""

from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db.tables import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    from app.db.tables import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind)
