import re
import uuid
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict

HTML_TAG_RE = re.compile(r"<[^>]+>")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?$")


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def ensure_no_html(value: str, field_name: str) -> str:
    if HTML_TAG_RE.search(value):
        raise ValueError(f"{field_name} must not contain HTML")
    return value


def ensure_no_control_chars(value: str, field_name: str) -> str:
    if CONTROL_CHAR_RE.search(value):
        raise ValueError(f"{field_name} contains unsupported control characters")
    return value


def normalize_text(
    value: str,
    field_name: str,
    *,
    max_length: int | None = None,
    allow_empty: bool = False,
) -> str:
    cleaned = value.strip()
    if not cleaned and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    ensure_no_html(cleaned, field_name)
    ensure_no_control_chars(cleaned, field_name)
    if max_length is not None and len(cleaned) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return cleaned


def normalize_optional_text(
    value: str | None,
    field_name: str,
    *,
    max_length: int | None = None,
) -> str | None:
    if value is None:
        return None
    cleaned = normalize_text(value, field_name, max_length=max_length, allow_empty=True)
    return cleaned or None


def validate_timezone_name(value: str) -> str:
    cleaned = normalize_text(value, "timezone", max_length=100)
    try:
        ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone must be a valid IANA timezone") from exc
    return cleaned


def validate_language_code(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = normalize_text(value, "language", max_length=10)
    if not LANGUAGE_RE.fullmatch(cleaned):
        raise ValueError("language must be a short locale code like 'en' or 'ru'")
    return cleaned


def validate_relative_or_http_url(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = normalize_text(value, "photo_url", max_length=500, allow_empty=True)
    if not cleaned:
        return None
    if cleaned.startswith("/"):
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("photo_url must be an absolute http(s) URL or an app-relative path")
    return cleaned


def validate_uuid_csv(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = normalize_text(value, field_name, max_length=500, allow_empty=True)
    if not cleaned:
        return None
    normalized_values: list[str] = []
    for item in cleaned.split(","):
        part = item.strip()
        if not part:
            continue
        try:
            normalized_values.append(str(uuid.UUID(part)))
        except ValueError as exc:
            raise ValueError(f"{field_name} must contain comma-separated UUIDs") from exc
    return ",".join(normalized_values) or None


def ensure_timezone_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")
    return value
