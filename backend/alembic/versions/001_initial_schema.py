"""Initial schema with all tables and stability_checked column

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
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=100), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_players_email"), "players", ["email"], unique=True)
    op.create_index(op.f("ix_players_id"), "players", ["id"], unique=False)
    op.create_index(
        op.f("ix_players_username"), "players", ["username"], unique=True
    )

    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("default_gold", sa.Integer(), nullable=False),
        sa.Column("default_bonds", sa.Integer(), nullable=False),
        sa.Column("default_territories", sa.Integer(), nullable=False),
        sa.Column("default_goods", sa.Integer(), nullable=False),
        sa.Column("default_people", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_countries_id"), "countries", ["id"], unique=False)

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=False),
        sa.Column("rounds_remaining", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=20), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stability_checked", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_games_id"), "games", ["id"], unique=False)

    op.create_table(
        "spawned_countries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("country_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("gold", sa.Integer(), nullable=False),
        sa.Column("bonds", sa.Integer(), nullable=False),
        sa.Column("territories", sa.Integer(), nullable=False),
        sa.Column("goods", sa.Integer(), nullable=False),
        sa.Column("people", sa.Integer(), nullable=False),
        sa.Column("banks", sa.Integer(), nullable=False),
        sa.Column("supporters", sa.Integer(), nullable=False),
        sa.Column("revolters", sa.Integer(), nullable=False),
        sa.Column("development_completed", sa.Boolean(), nullable=True),
        sa.Column("actions_completed", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"]),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_spawned_countries_id"), "spawned_countries", ["id"], unique=False
    )

    op.create_table(
        "game_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("spawned_country_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["spawned_country_id"], ["spawned_countries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_game_history_id"), "game_history", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_game_history_id"), table_name="game_history")
    op.drop_table("game_history")
    op.drop_index(op.f("ix_spawned_countries_id"), table_name="spawned_countries")
    op.drop_table("spawned_countries")
    op.drop_index(op.f("ix_games_id"), table_name="games")
    op.drop_table("games")
    op.drop_index(op.f("ix_countries_id"), table_name="countries")
    op.drop_table("countries")
    op.drop_index(op.f("ix_players_username"), table_name="players")
    op.drop_index(op.f("ix_players_id"), table_name="players")
    op.drop_index(op.f("ix_players_email"), table_name="players")
    op.drop_table("players")
