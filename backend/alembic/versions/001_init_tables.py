"""init tables

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),                  nullable=False),
        sa.Column("email",           sa.String(),                   nullable=False),
        sa.Column("full_name",       sa.String(),                   nullable=False),
        sa.Column("hashed_password", sa.String(),                   nullable=False),
        sa.Column("is_active",       sa.Boolean(),  server_default="true",  nullable=False),
        sa.Column("is_verified",     sa.Boolean(),  server_default="false", nullable=False),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id",    "users", ["id"],    unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id",         sa.Integer(), nullable=False),
        sa.Column("token",      sa.String(),  nullable=False),
        sa.Column("user_id",    sa.Integer(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_id",    "refresh_tokens", ["id"],    unique=False)
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)

    # ── jobs ─────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id",          sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(),  nullable=False),
        sa.Column("title",       sa.String(),  nullable=False),
        sa.Column("company",     sa.String(),  nullable=True),
        sa.Column("location",    sa.String(),  nullable=True),
        sa.Column("description", sa.String(),  nullable=True),
        sa.Column("salary_min",  sa.Integer(), nullable=True),
        sa.Column("salary_max",  sa.Integer(), nullable=True),
        sa.Column("url",         sa.String(),  nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_id",          "jobs", ["id"],          unique=False)
    op.create_index("ix_jobs_external_id", "jobs", ["external_id"], unique=True)

    # ── saved_jobs ────────────────────────────────────────────────────────────
    op.create_table(
        "saved_jobs",
        sa.Column("id",         sa.Integer(), nullable=False),
        sa.Column("user_id",    sa.Integer(), nullable=False),
        sa.Column("job_id",     sa.Integer(), nullable=False),
        sa.Column("status",     sa.String(),  server_default="saved", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"],  ["jobs.id"],  ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_jobs_id", "saved_jobs", ["id"], unique=False)

    # ── notes ─────────────────────────────────────────────────────────────────
    op.create_table(
        "notes",
        sa.Column("id",           sa.Integer(), nullable=False),
        sa.Column("user_id",      sa.Integer(), nullable=False),
        sa.Column("saved_job_id", sa.Integer(), nullable=False),
        sa.Column("content",      sa.Text(),    nullable=False),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"],      ["users.id"],      ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saved_job_id"], ["saved_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_id", "notes", ["id"], unique=False)


def downgrade():
    op.drop_table("notes")
    op.drop_table("saved_jobs")
    op.drop_table("jobs")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
