"""Scrub secrets from telemetry attributes / custody metadata (PROJETOSIN-199)."""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

# Header / key names (case-insensitive) that must never leave the process.
_SENSITIVE_KEY_RE = re.compile(
    r"(authorization|api[_-]?key|session[_-]?api[_-]?key|x-session-api-key|"
    r"password|passwd|secret|token|cookie|set-cookie|"
    r"msf[_-]?pass|gvm[_-]?pass|bearer)",
    re.IGNORECASE,
)

# Inline values that look like credentials.
_SENSITIVE_VALUE_RE = re.compile(
    r"(?i)\b(bearer\s+[a-z0-9._\-+/=]{8,}|sk-[a-z0-9]{20,}|"
    r"ghp_[a-z0-9]{20,}|xox[baprs]-[a-z0-9-]{10,})"
)


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(str(key)))


def redact_string(value: str) -> str:
    if not value:
        return value
    if _SENSITIVE_VALUE_RE.search(value):
        return _SENSITIVE_VALUE_RE.sub(REDACTED, value)
    return value


def redact_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, (list, tuple)):
        return [redact_value(v) for v in value]
    return value


def redact_mapping(data: dict[str, Any] | None) -> dict[str, Any]:
    """Return a deep-copied mapping with sensitive keys/values scrubbed."""
    if not data:
        return {}
    out: dict[str, Any] = {}
    for key, value in data.items():
        key_str = str(key)
        if is_sensitive_key(key_str):
            out[key_str] = REDACTED
        else:
            out[key_str] = redact_value(value)
    return out
