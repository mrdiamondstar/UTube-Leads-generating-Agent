"""subscription payment_ref

Revision ID: 0006_payment_ref
Revises: 0005_niches
Create Date: 2026-07-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_payment_ref"
down_revision: Union[str, None] = "0005_niches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("payment_ref", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("subscriptions", "payment_ref")
