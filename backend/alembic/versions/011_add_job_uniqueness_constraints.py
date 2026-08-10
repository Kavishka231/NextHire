"""add job uniqueness constraints

Revision ID: 011
Revises: 010
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def _require_no_existing_duplicates() -> None:
    connection = op.get_bind()
    duplicate_saved_job = connection.execute(sa.text("""
        SELECT user_id, job_id
        FROM saved_jobs
        GROUP BY user_id, job_id
        HAVING COUNT(*) > 1
        LIMIT 1
    """)).first()
    if duplicate_saved_job:
        raise RuntimeError(
            "Cannot add saved-job uniqueness: resolve duplicate "
            f"user_id={duplicate_saved_job.user_id}, job_id={duplicate_saved_job.job_id} first"
        )

    duplicate_application = connection.execute(sa.text("""
        SELECT applicant_user_id, job_id
        FROM job_applications
        WHERE applicant_user_id IS NOT NULL
        GROUP BY applicant_user_id, job_id
        HAVING COUNT(*) > 1
        LIMIT 1
    """)).first()
    if duplicate_application:
        raise RuntimeError(
            "Cannot add application uniqueness: resolve duplicate "
            f"applicant_user_id={duplicate_application.applicant_user_id}, "
            f"job_id={duplicate_application.job_id} first"
        )


def upgrade():
    # Refuse to silently discard user data. Operators must explicitly resolve
    # any historical duplicates before applying these constraints.
    _require_no_existing_duplicates()
    op.create_unique_constraint(
        "uq_saved_jobs_user_job",
        "saved_jobs",
        ["user_id", "job_id"],
    )
    op.create_unique_constraint(
        "uq_job_applications_applicant_job",
        "job_applications",
        ["applicant_user_id", "job_id"],
    )


def downgrade():
    op.drop_constraint(
        "uq_job_applications_applicant_job",
        "job_applications",
        type_="unique",
    )
    op.drop_constraint(
        "uq_saved_jobs_user_job",
        "saved_jobs",
        type_="unique",
    )
