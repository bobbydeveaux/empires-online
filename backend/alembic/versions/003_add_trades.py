"""Add trades table for trading system

Revision ID: 003
Revises: 002
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("proposer_country_id", sa.Integer(), nullable=False),
        sa.Column("receiver_country_id", sa.Integer(), nullable=False),
        sa.Column("offer_gold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offer_people", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offer_territory", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_gold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_people", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_territory", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["proposer_country_id"], ["spawned_countries.id"]),
        sa.ForeignKeyConstraint(["receiver_country_id"], ["spawned_countries.id"]),
        sa.CheckConstraint(
            "proposer_country_id != receiver_country_id", name="no_self_trade"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trades_id"), "trades", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_trades_id"), table_name="trades")
    op.drop_table("trades")
