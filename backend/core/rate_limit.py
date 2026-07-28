from dataclasses import dataclass

from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

from app.config import settings


_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


@dataclass(frozen=True)
class RateLimit:
    bucket: str
    requests: int
    window_seconds: int = 60

    def __call__(self, request: Request) -> None:
        # Unit/API tests do not require a running Redis service. Rate-limit
        # behavior is covered separately with a deterministic fake client.
        if settings.ENVIRONMENT.lower() == "testing":
            return

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate-limit:{self.bucket}:{client_ip}"
        try:
            count = _client.incr(key)
            if count == 1:
                _client.expire(key, self.window_seconds)
            ttl = _client.ttl(key)
        except RedisError as exc:
            raise HTTPException(
                status_code=503,
                detail="Rate-limit service unavailable",
            ) from exc

        if count > self.requests:
            retry_after = ttl if ttl and ttl > 0 else self.window_seconds
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(retry_after)},
            )


def rate_limit(bucket: str, requests: int, window_seconds: int = 60) -> RateLimit:
    return RateLimit(bucket, requests, window_seconds)
