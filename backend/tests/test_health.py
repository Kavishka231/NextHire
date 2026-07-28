from unittest.mock import Mock, patch


def test_liveness(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_checks_database_and_redis(client):
    redis_client = Mock()
    with patch("main.Redis.from_url", return_value=redis_client):
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok", "redis": "ok"}
    redis_client.ping.assert_called_once()
