"""add admin fields and search logs

Revision ID: 003
Revises: 002
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("admin_role", sa.String(), server_default="user", nullable=False))
    op.add_column("users", sa.Column("banned_until", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("last_active_at", sa.DateTime(), nullable=True))
    op.add_column("jobs", sa.Column("category", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("is_featured", sa.Boolean(), server_default="false", nullable=False))
    op.create_table(
        "search_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keywords", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_logs_id", "search_logs", ["id"], unique=False)


def downgrade():
    op.drop_index("ix_search_logs_id", table_name="search_logs")
    op.drop_table("search_logs")
    op.drop_column("jobs", "is_featured")
    op.drop_column("jobs", "category")
    op.drop_column("users", "last_active_at")
    op.drop_column("users", "banned_until")
    op.drop_column("users", "admin_role")
    op.drop_column("users", "is_admin")
