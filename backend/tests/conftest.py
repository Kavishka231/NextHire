import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    payload = {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "password123",
    }
    client.post("/api/v1/auth/register", json=payload)
    return payload


@pytest.fixture
def auth_headers(client, registered_user):
    res = client.post("/api/v1/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def saved_job_id(client, auth_headers):
    """Search (caches mock jobs), then save the first one. Returns saved_job id."""
    search = client.get("/api/v1/search/jobs", params={"keywords": "developer"}, headers=auth_headers)
    ext_id = search.json()["jobs"][0]["external_id"]
    save   = client.post("/api/v1/saved-jobs", json={"external_id": ext_id}, headers=auth_headers)
    return save.json()["id"]
