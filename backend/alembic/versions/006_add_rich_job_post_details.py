"""add rich job post details

Revision ID: 006
Revises: 005
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("role_overview", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("company_description", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("additional_qualifications", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("schedule_expectations", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("jobs", "schedule_expectations")
    op.drop_column("jobs", "additional_qualifications")
    op.drop_column("jobs", "company_description")
    op.drop_column("jobs", "role_overview")
