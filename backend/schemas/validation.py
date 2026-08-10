import json
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from pydantic import EmailStr, TypeAdapter


EMAIL_ADAPTER = TypeAdapter(EmailStr)
MAX_URL_LENGTH = 2048
MAX_PROFILE_COLLECTION_ITEMS = 25
MAX_PROFILE_ENTRY_KEYS = 20
MAX_PROFILE_JSON_BYTES = 50_000
MAX_PROFILE_JSON_DEPTH = 3
MAX_PROFILE_JSON_NODES = 250


def optional_http_url(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return ""
    if len(value) > MAX_URL_LENGTH:
        raise ValueError("URL must not exceed 2048 characters")
    if "\\" in value or any(character.isspace() for character in value):
        raise ValueError("URL must not contain whitespace or backslashes")
    parsed = urlsplit(value)
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("URL contains an invalid port") from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("URL must be an HTTP or HTTPS URL without embedded credentials")
    return value


def optional_email(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return ""
    return str(EMAIL_ADAPTER.validate_python(value))


def optional_iso_date(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return ""
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Date must use YYYY-MM-DD format") from exc
    return value


def validate_salary_range(minimum: int | None, maximum: int | None) -> None:
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("Minimum salary must not exceed maximum salary")


def _validate_json_value(value: Any, depth: int, counter: list[int]) -> None:
    counter[0] += 1
    if counter[0] > MAX_PROFILE_JSON_NODES:
        raise ValueError("Profile collection is too complex")
    if depth > MAX_PROFILE_JSON_DEPTH:
        raise ValueError("Profile collection nesting is too deep")
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if len(value) > 2_000:
            raise ValueError("Profile collection text must not exceed 2000 characters")
        return
    if isinstance(value, list):
        if len(value) > MAX_PROFILE_COLLECTION_ITEMS:
            raise ValueError("Nested profile lists must not exceed 25 items")
        for item in value:
            _validate_json_value(item, depth + 1, counter)
        return
    if isinstance(value, dict):
        if len(value) > MAX_PROFILE_ENTRY_KEYS:
            raise ValueError("Profile entries must not exceed 20 fields")
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 64:
                raise ValueError("Profile entry keys must be 1 to 64 characters")
            _validate_json_value(item, depth + 1, counter)
        return
    raise ValueError("Profile collections may contain only JSON-compatible values")


def validate_profile_collection(value: list[dict[str, Any]] | None):
    if value is None:
        return None
    if len(value) > MAX_PROFILE_COLLECTION_ITEMS:
        raise ValueError("Profile collections must not exceed 25 items")
    try:
        encoded_size = len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Profile collections must contain valid JSON values") from exc
    if encoded_size > MAX_PROFILE_JSON_BYTES:
        raise ValueError("Profile collection must not exceed 50000 bytes")
    _validate_json_value(value, 0, [0])
    return value
