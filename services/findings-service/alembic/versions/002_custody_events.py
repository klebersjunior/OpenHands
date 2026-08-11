"""custody_events table (PROJETOSIN-199).

Revision ID: 002
Revises: 001
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custody_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("engagement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor", sa.String(256), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(256), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("metadata_redacted", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "idx_custody_events_engagement_id", "custody_events", ["engagement_id"]
    )
    op.create_index("idx_custody_events_ts", "custody_events", ["ts"])


def downgrade() -> None:
    op.drop_index("idx_custody_events_ts", table_name="custody_events")
    op.drop_index("idx_custody_events_engagement_id", table_name="custody_events")
    op.drop_table("custody_events")
