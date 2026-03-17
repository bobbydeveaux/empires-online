"""Add stability_checked column to games table

Revision ID: 001
Revises:
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("stability_checked", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("games", "stability_checked")
