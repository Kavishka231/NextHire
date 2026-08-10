"""add user token version

Revision ID: 010
Revises: 009
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    # Access tokens issued before this release do not carry token_version and
    # are therefore intentionally rejected after deployment.
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.alter_column("users", "token_version", server_default=None)


def downgrade():
    op.drop_column("users", "token_version")
