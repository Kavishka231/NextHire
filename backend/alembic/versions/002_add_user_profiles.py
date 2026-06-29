"""add user profiles

Revision ID: 002
Revises: 001
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("headline", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("open_to_work", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("linkedin_url", sa.String(), nullable=True),
        sa.Column("github_url", sa.String(), nullable=True),
        sa.Column("portfolio_url", sa.String(), nullable=True),
        sa.Column("desired_job_title", sa.String(), nullable=True),
        sa.Column("preferred_job_type", sa.String(), nullable=True),
        sa.Column("preferred_work_style", sa.String(), nullable=True),
        sa.Column("preferred_locations", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("expected_salary_min", sa.Integer(), nullable=True),
        sa.Column("expected_salary_max", sa.Integer(), nullable=True),
        sa.Column("industries", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("available_immediately", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("resume_file_name", sa.String(), nullable=True),
        sa.Column("resume_url", sa.String(), nullable=True),
        sa.Column("resume_visible_to_recruiters", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("work_experience", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("education", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("skills", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("certifications", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("projects", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("languages", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("volunteer_experience", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("achievements", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_user_profiles_id", "user_profiles", ["id"], unique=False)


def downgrade():
    op.drop_index("ix_user_profiles_id", table_name="user_profiles")
    op.drop_table("user_profiles")
