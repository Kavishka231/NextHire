from fastapi import HTTPException
from redis.exceptions import ConnectionError
from starlette.requests import Request

from app.config import settings
from core import rate_limit as rate_limit_module
from core.rate_limit import RateLimit


class FakeRedis:
    def __init__(self):
        self.counts = {}
        self.expirations = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        self.expirations[key] = seconds

    def ttl(self, key):
        return self.expirations.get(key, -1)


def _request(ip="203.0.113.10"):
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [],
        "client": (ip, 50000),
        "server": ("testserver", 80),
        "scheme": "http",
    })


def test_rate_limit_returns_429_with_retry_after(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "_client", fake_redis)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    limiter = RateLimit("login", requests=2, window_seconds=60)

    limiter(_request())
    limiter(_request())

    try:
        limiter(_request())
        raise AssertionError("Expected the rate limit to reject the request")
    except HTTPException as exc:
        assert exc.status_code == 429
        assert exc.headers["Retry-After"] == "60"


def test_rate_limit_separates_clients(monkeypatch):
    monkeypatch.setattr(rate_limit_module, "_client", FakeRedis())
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    limiter = RateLimit("login", requests=1)

    limiter(_request("203.0.113.10"))
    limiter(_request("203.0.113.11"))


def test_rate_limit_fails_closed_when_redis_is_unavailable(monkeypatch):
    class BrokenRedis:
        def incr(self, key):
            raise ConnectionError("Redis unavailable")

    monkeypatch.setattr(rate_limit_module, "_client", BrokenRedis())
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    try:
        RateLimit("login", requests=1)(_request())
        raise AssertionError("Expected unavailable Redis to reject the request")
    except HTTPException as exc:
        assert exc.status_code == 503
