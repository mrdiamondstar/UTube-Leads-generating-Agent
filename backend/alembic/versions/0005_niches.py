"""niches

Revision ID: 0005_niches
Revises: 0004_users
Create Date: 2026-07-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_niches"
down_revision: Union[str, None] = "0004_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "niches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("popularity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_niche_name"),
    )
    op.create_index("ix_niches_name", "niches", ["name"])
    op.create_index("ix_niches_category", "niches", ["category"])


def downgrade() -> None:
    op.drop_index("ix_niches_category", table_name="niches")
    op.drop_index("ix_niches_name", table_name="niches")
    op.drop_table("niches")
