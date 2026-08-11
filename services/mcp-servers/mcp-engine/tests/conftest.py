"""Shared fixtures for mcp-engine tests."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = Path(__file__).resolve().parents[1]
for path in (ROOT, ENGINE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Stable id — avoid uuid4() (conftest can be imported as both conftest and tests.conftest).
ENGAGEMENT_ID = "00000000-0000-4000-8000-000000000197"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PENTEST_SCOPE_ALLOWLIST", "example.com,*.lab.local")
    monkeypatch.setenv("PENTEST_AUTONOMY_MODE", "semi_autonomous")
    monkeypatch.setenv("SESSION_API_KEY", "test-session-key")
    monkeypatch.setenv("FINDINGS_SERVICE_URL", "http://findings.test")
    monkeypatch.setenv("ENGAGEMENT_ID", ENGAGEMENT_ID)
    monkeypatch.setenv("PENTEST_ENGINE_MOCK", "1")
    monkeypatch.delenv("PENTEST_ENGINE_CAI_ENABLED", raising=False)
    monkeypatch.delenv("PENTEST_CAPABILITIES", raising=False)
    monkeypatch.delenv("PENTEST_ENGINE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("PENTEST_ENGINE_URL_ALLOWLIST", raising=False)
    monkeypatch.delenv("PENTEST_ENGINE_PENTESTAGENT_URL", raising=False)
    monkeypatch.delenv("PENTEST_ENGINE_CAI_URL", raising=False)

    from adapters.base import reset_run_registry
    from shared.confirmation import clear_confirmation_state

    clear_confirmation_state()
    reset_run_registry()
    yield
    clear_confirmation_state()
    reset_run_registry()


class FakeFindingsTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.posts: list[dict] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("X-Session-API-Key")
        if not auth:
            return httpx.Response(401, json={"detail": "Unauthorized"})
        body = json.loads(request.content.decode())
        self.posts.append(body)
        return httpx.Response(
            201,
            json={
                "id": str(uuid.uuid4()),
                "engagement_id": body["engagement_id"],
                "source_tool": body["source_tool"],
                "title": body["title"],
                "severity": body["severity"],
                "status": "new",
            },
        )
