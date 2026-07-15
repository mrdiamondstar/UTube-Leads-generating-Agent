"""subscriptions

Revision ID: 0003_subscriptions
Revises: 0002_videos_quota
Create Date: 2026-07-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_subscriptions"
down_revision: Union[str, None] = "0002_videos_quota"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("customer_email", sa.String(length=255), nullable=False),
        sa.Column("plan_id", sa.String(length=32), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_subscriptions_customer_email", "subscriptions", ["customer_email"]
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_customer_email", table_name="subscriptions")
    op.drop_table("subscriptions")
