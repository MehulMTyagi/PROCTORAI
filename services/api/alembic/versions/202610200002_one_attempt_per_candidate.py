"""enforce one attempt per candidate and assessment

Revision ID: 202610200002
Revises: 202610200001
Create Date: 2026-10-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202610200002"
down_revision: str | None = "202610200001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("attempts") as batch_op:
        batch_op.create_unique_constraint(
            "uq_attempt_assessment_candidate", ["assessment_id", "candidate_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("attempts") as batch_op:
        batch_op.drop_constraint("uq_attempt_assessment_candidate", type_="unique")
