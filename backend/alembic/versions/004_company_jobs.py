"""add company accounts and owned job posts

Revision ID: 004
Revises: 003
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("account_type", sa.String(), server_default="candidate", nullable=False))
    op.add_column("users", sa.Column("company_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("company_website", sa.String(), nullable=True))
    op.add_column("users", sa.Column("company_description", sa.String(), nullable=True))
    op.add_column("users", sa.Column("company_status", sa.String(), server_default="none", nullable=False))
    op.add_column("users", sa.Column("company_verified", sa.Boolean(), server_default="false", nullable=False))

    op.add_column("jobs", sa.Column("source", sa.String(), server_default="adzuna", nullable=False))
    op.add_column("jobs", sa.Column("posted_by_user_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("employment_type", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("work_style", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("experience_level", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("requirements", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("responsibilities", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("benefits", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("application_email", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("application_url", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("application_instructions", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("deadline", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))
    op.create_foreign_key("fk_jobs_posted_by_user_id", "jobs", "users", ["posted_by_user_id"], ["id"])


def downgrade():
    op.drop_constraint("fk_jobs_posted_by_user_id", "jobs", type_="foreignkey")
    for column in [
        "is_active", "deadline", "application_instructions", "application_url", "application_email",
        "benefits", "responsibilities", "requirements", "experience_level", "work_style",
        "employment_type", "posted_by_user_id", "source",
    ]:
        op.drop_column("jobs", column)
    for column in [
        "company_verified", "company_status", "company_description", "company_website",
        "company_name", "account_type",
    ]:
        op.drop_column("users", column)
