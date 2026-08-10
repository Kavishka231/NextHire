"""validate application status

Revision ID: 012
Revises: 011
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    invalid_status = connection.execute(
        sa.text("""
            SELECT id, status
            FROM job_applications
            WHERE status NOT IN (
                'submitted', 'reviewing', 'shortlisted', 'interview',
                'offered', 'rejected', 'withdrawn'
            )
            LIMIT 1
        """)
    ).first()
    if invalid_status:
        raise RuntimeError(
            "Cannot add application-status constraint: resolve invalid "
            f"application id={invalid_status.id}, status={invalid_status.status!r} first"
        )
    op.create_check_constraint(
        "ck_job_applications_status_valid",
        "job_applications",
        "status IN ('submitted', 'reviewing', 'shortlisted', 'interview', "
        "'offered', 'rejected', 'withdrawn')",
    )


def downgrade():
    op.drop_constraint(
        "ck_job_applications_status_valid",
        "job_applications",
        type_="check",
    )
