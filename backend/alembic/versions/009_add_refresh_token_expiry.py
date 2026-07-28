"""add refresh token expiry

Revision ID: 009
Revises: 008
Create Date: 2026-07-28
"""
from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    # Existing sessions expire during this security migration. Users must log
    # in again; newly issued tokens always receive their configured lifetime.
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.alter_column("refresh_tokens", "expires_at", server_default=None)
    op.create_index(
        "ix_refresh_tokens_expires_at",
        "refresh_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "expires_at")
