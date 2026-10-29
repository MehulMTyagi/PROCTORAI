"""add roster fields for admin-provisioned student accounts

Revision ID: 202610230002
Revises: 202610230001
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202610230002"
down_revision: str | None = "202610230001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("roll_number", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("program", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("admission_year", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("section", sa.String(length=100), nullable=True))
    op.create_index("ix_users_roll_number", "users", ["roll_number"], unique=True)
    op.create_index("ix_users_program", "users", ["program"])
    op.create_index("ix_users_admission_year", "users", ["admission_year"])
    op.create_index("ix_users_section", "users", ["section"])


def downgrade() -> None:
    op.drop_index("ix_users_section", table_name="users")
    op.drop_index("ix_users_admission_year", table_name="users")
    op.drop_index("ix_users_program", table_name="users")
    op.drop_index("ix_users_roll_number", table_name="users")
    op.drop_column("users", "section")
    op.drop_column("users", "admission_year")
    op.drop_column("users", "program")
    op.drop_column("users", "roll_number")
