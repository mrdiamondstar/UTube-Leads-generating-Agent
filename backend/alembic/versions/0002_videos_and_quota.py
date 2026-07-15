"""videos + api quota usage; channel.uploads_playlist_id

Revision ID: 0002_videos_quota
Revises: 0001_initial
Create Date: 2026-07-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_videos_quota"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "channels", sa.Column("uploads_playlist_id", sa.String(length=64), nullable=True)
    )

    op.create_table(
        "videos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("channel_id", sa.String(length=36), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("youtube_video_id", name="uq_video_yt_id"),
    )
    op.create_index("ix_videos_youtube_video_id", "videos", ["youtube_video_id"])

    op.create_table(
        "api_quota_usage",
        sa.Column("day", sa.String(length=10), primary_key=True),
        sa.Column("units_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calls", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("api_quota_usage")
    op.drop_index("ix_videos_youtube_video_id", table_name="videos")
    op.drop_table("videos")
    op.drop_column("channels", "uploads_playlist_id")
