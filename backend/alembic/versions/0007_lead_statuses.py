"""lead statuses (per-user outreach status)

Revision ID: 0007_lead_statuses
Revises: 0006_payment_ref
Create Date: 2026-07-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_lead_statuses"
down_revision: Union[str, None] = "0006_payment_ref"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lead_statuses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            sa.String(length=36),
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "channel_id", name="uq_lead_status_user_channel"),
    )
    op.create_index("ix_lead_statuses_user_id", "lead_statuses", ["user_id"])
    op.create_index("ix_lead_statuses_channel_id", "lead_statuses", ["channel_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_statuses_channel_id", table_name="lead_statuses")
    op.drop_index("ix_lead_statuses_user_id", table_name="lead_statuses")
    op.drop_table("lead_statuses")
