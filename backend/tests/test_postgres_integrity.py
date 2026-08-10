import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


POSTGRES_TEST_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="POSTGRES_TEST_DATABASE_URL is required for PostgreSQL integrity tests",
)


@pytest.fixture
def postgres_connection():
    engine = create_engine(POSTGRES_TEST_DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()


def _create_user_and_job(connection):
    suffix = uuid4().hex
    user_id = connection.execute(
        text("""
            INSERT INTO users (email, full_name, hashed_password, token_version)
            VALUES (:email, 'Integrity Test User', 'test-only-hash', 0)
            RETURNING id
        """),
        {"email": f"integrity-{suffix}@example.com"},
    ).scalar_one()
    job_id = connection.execute(
        text("""
            INSERT INTO jobs (external_id, title)
            VALUES (:external_id, 'Integrity Test Job')
            RETURNING id
        """),
        {"external_id": f"integrity-{suffix}"},
    ).scalar_one()
    return user_id, job_id


def test_postgres_rejects_duplicate_saved_job(postgres_connection):
    user_id, job_id = _create_user_and_job(postgres_connection)
    postgres_connection.execute(
        text("INSERT INTO saved_jobs (user_id, job_id) VALUES (:user_id, :job_id)"),
        {"user_id": user_id, "job_id": job_id},
    )

    with pytest.raises(IntegrityError):
        postgres_connection.execute(
            text("INSERT INTO saved_jobs (user_id, job_id) VALUES (:user_id, :job_id)"),
            {"user_id": user_id, "job_id": job_id},
        )


def test_postgres_rejects_duplicate_application(postgres_connection):
    user_id, job_id = _create_user_and_job(postgres_connection)
    parameters = {
        "user_id": user_id,
        "job_id": job_id,
        "email": f"applicant-{uuid4().hex}@example.com",
    }
    statement = text("""
        INSERT INTO job_applications (
            job_id,
            applicant_user_id,
            applicant_name,
            applicant_email
        ) VALUES (
            :job_id,
            :user_id,
            'Integrity Test Applicant',
            :email
        )
    """)
    postgres_connection.execute(statement, parameters)

    with pytest.raises(IntegrityError):
        postgres_connection.execute(statement, parameters)


def test_postgres_rejects_invalid_application_status(postgres_connection):
    user_id, job_id = _create_user_and_job(postgres_connection)
    with pytest.raises(IntegrityError):
        postgres_connection.execute(
            text("""
                INSERT INTO job_applications (
                    job_id,
                    applicant_user_id,
                    applicant_name,
                    applicant_email,
                    status
                ) VALUES (
                    :job_id,
                    :user_id,
                    'Integrity Test Applicant',
                    :email,
                    'hired'
                )
            """),
            {
                "job_id": job_id,
                "user_id": user_id,
                "email": f"invalid-status-{uuid4().hex}@example.com",
            },
        )
