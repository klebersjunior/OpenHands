"""Orchestration runs and steps (PROJETOSIN-196).

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
        "orchestration_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("playbook_id", sa.String(128), nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("engine_id", sa.String(64), nullable=False),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="pending"
        ),
        sa.Column("current_phase", sa.String(64), nullable=True),
        sa.Column(
            "finding_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ("
            "'pending','running','awaiting_confirmation',"
            "'succeeded','failed','cancelled')",
            name="orchestration_runs_status_check",
        ),
    )
    op.create_index(
        "idx_orchestration_runs_engagement_id",
        "orchestration_runs",
        ["engagement_id"],
    )

    op.create_table(
        "orchestration_steps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orchestration_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("phase_id", sa.String(64), nullable=False),
        sa.Column("engine_phase", sa.String(64), nullable=False),
        sa.Column(
            "gate", sa.String(32), nullable=False, server_default="none"
        ),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="pending"
        ),
        sa.Column("engine_run_id", sa.String(128), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "finding_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_orchestration_steps_run_id",
        "orchestration_steps",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_orchestration_steps_run_id", table_name="orchestration_steps")
    op.drop_table("orchestration_steps")
    op.drop_index(
        "idx_orchestration_runs_engagement_id", table_name="orchestration_runs"
    )
    op.drop_table("orchestration_runs")
