"""add job applications

Revision ID: 007
Revises: 006
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("applicant_user_id", sa.Integer(), nullable=True),
        sa.Column("applicant_name", sa.String(), nullable=False),
        sa.Column("applicant_email", sa.String(), nullable=False),
        sa.Column("applicant_phone", sa.String(), nullable=True),
        sa.Column("headline", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("linkedin_url", sa.String(), nullable=True),
        sa.Column("github_url", sa.String(), nullable=True),
        sa.Column("portfolio_url", sa.String(), nullable=True),
        sa.Column("resume_url", sa.String(), nullable=True),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column("extra_details", sa.Text(), nullable=True),
        sa.Column("use_profile", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("status", sa.String(), server_default="submitted", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["applicant_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_applications_id", "job_applications", ["id"], unique=False)
    op.create_index("ix_job_applications_job_id", "job_applications", ["job_id"], unique=False)
    op.create_index("ix_job_applications_applicant_user_id", "job_applications", ["applicant_user_id"], unique=False)


def downgrade():
    op.drop_index("ix_job_applications_applicant_user_id", table_name="job_applications")
    op.drop_index("ix_job_applications_job_id", table_name="job_applications")
    op.drop_index("ix_job_applications_id", table_name="job_applications")
    op.drop_table("job_applications")
