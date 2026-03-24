"""Add game_results table for tracking completed game outcomes

Revision ID: 002
Revises: 001
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("winner_country_id", sa.Integer(), nullable=False),
        sa.Column("winner_player_id", sa.Integer(), nullable=False),
        sa.Column("duration_rounds", sa.Integer(), nullable=False),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("final_rankings", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["winner_country_id"], ["spawned_countries.id"]),
        sa.ForeignKeyConstraint(["winner_player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id"),
    )
    op.create_index(op.f("ix_game_results_id"), "game_results", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_game_results_id"), table_name="game_results")
    op.drop_table("game_results")
