"""AC-199-2 — redaction removes session key / Authorization from log attrs."""

from __future__ import annotations

import sys
from pathlib import Path

SERVICES_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICES_ROOT))

from shared.redaction import REDACTED, redact_mapping


def test_ac_199_2_redacts_session_and_authorization():
    scrubbed = redact_mapping(
        {
            "Authorization": "Bearer super-secret-token",
            "X-Session-API-Key": "session-abc-1234567890",
            "x-session-api-key": "also-secret",
            "api_key": "sk-live-should-go",
            "password": "hunter2",
            "safe_tool": "nuclei",
            "nested": {
                "cookie": "sid=abc",
                "target": "example.com",
            },
            "note": "Authorization: Bearer leaked-inline-token-value",
        }
    )
    assert scrubbed["Authorization"] == REDACTED
    assert scrubbed["X-Session-API-Key"] == REDACTED
    assert scrubbed["x-session-api-key"] == REDACTED
    assert scrubbed["api_key"] == REDACTED
    assert scrubbed["password"] == REDACTED
    assert scrubbed["safe_tool"] == "nuclei"
    assert scrubbed["nested"]["cookie"] == REDACTED
    assert scrubbed["nested"]["target"] == "example.com"
    assert REDACTED in scrubbed["note"]
    assert "leaked-inline-token-value" not in scrubbed["note"]
