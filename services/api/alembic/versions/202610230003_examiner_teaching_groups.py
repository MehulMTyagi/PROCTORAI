"""restrict examiner candidate access to assigned teaching groups

Revision ID: 202610230003
Revises: 202610230002
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202610230003"
down_revision: str | None = "202610230002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "teaching_group_assignments",
        sa.Column("examiner_id", sa.Uuid(), nullable=False),
        sa.Column("program", sa.String(length=100), nullable=False),
        sa.Column("admission_year", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=100), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["examiner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "examiner_id",
            "program",
            "admission_year",
            "section",
            name="uq_examiner_teaching_group",
        ),
    )
    op.create_index(
        "ix_teaching_group_assignments_examiner_id",
        "teaching_group_assignments",
        ["examiner_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_teaching_group_assignments_examiner_id",
        table_name="teaching_group_assignments",
    )
    op.drop_table("teaching_group_assignments")
