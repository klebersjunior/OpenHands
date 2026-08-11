"""AC-197-4 / AC-197-6 — adapter unit tests without real Docker images."""

from __future__ import annotations

import json

import pytest

from adapters.base import (
    RunRegistry,
    assert_allowed_engine_url,
    assert_no_ollama_llm,
)
from adapters.cai import CaiAdapter
from adapters.pentestagent import PentestAgentAdapter
from shared.findings_client import FindingsClient
from shared.normalize import normalize_finding
from tests.conftest import ENGAGEMENT_ID, FakeFindingsTransport
from tools.cancel_run import run_cancel_run
from tools.get_run import run_get_run
from tools.start_phase import run_start_phase


@pytest.mark.asyncio
async def test_ac_197_4_mock_findings_normalized_and_posted():
    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    body = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="scan",
            targets=["https://app.example.com"],
            findings=client,
        )
    )
    assert body["ok"] is True
    assert body["status"] == "succeeded"
    assert len(transport.posts) >= 1
    posted = transport.posts[0]
    # Same shape as normalize_finding
    expected_keys = set(
        normalize_finding(
            engagement_id=ENGAGEMENT_ID,
            source_tool="pentestagent",
            title="x",
            severity="info",
        ).keys()
    )
    assert expected_keys.issubset(posted.keys())
    assert posted["source_tool"] == "pentestagent"
    assert posted["engagement_id"] == ENGAGEMENT_ID

    got = json.loads(await run_get_run(run_id=body["run_id"]))
    assert got["ok"] is True
    assert got["status"] == "succeeded"
    assert isinstance(got["finding_ids"], list)
    assert len(got["finding_ids"]) >= 1


@pytest.mark.asyncio
async def test_ac_197_6_adapters_never_require_docker_images():
    """CI path uses mock — no image pull / docker socket."""
    registry = RunRegistry()
    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    pa = PentestAgentAdapter(findings=client, transport=transport)
    assert pa.status() == "ready"
    run = registry.create(
        engine_id="pentestagent",
        phase="analyze",
        engagement_id=ENGAGEMENT_ID,
        targets=["https://example.com"],
    )
    run = await pa.start(run=run, registry=registry)
    assert run.status == "succeeded"
    assert transport.posts

    cai = CaiAdapter(findings=client, transport=transport)
    # Flag off → disabled; enabling uses mock without images.
    assert cai.status() == "disabled"


@pytest.mark.asyncio
async def test_cai_mock_posts_findings_when_enabled(monkeypatch):
    monkeypatch.setenv("PENTEST_ENGINE_CAI_ENABLED", "true")
    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    body = json.loads(
        await run_start_phase(
            engine_id="cai",
            phase="analyze",
            targets=["https://example.com"],
            findings=client,
        )
    )
    assert body["ok"] is True
    assert transport.posts[0]["source_tool"] == "cai"


@pytest.mark.asyncio
async def test_cancel_run_best_effort():
    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)
    started = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="recon",
            targets=["https://example.com"],
            findings=client,
        )
    )
    cancelled = json.loads(await run_cancel_run(run_id=started["run_id"]))
    assert cancelled["ok"] is True


@pytest.mark.asyncio
async def test_loopback_engine_url_unavailable(monkeypatch):
    monkeypatch.setenv("PENTEST_ENGINE_MOCK", "0")
    monkeypatch.setenv("PENTEST_ENGINE_URL_ALLOWLIST", "engine-pentestagent")
    monkeypatch.setenv(
        "PENTEST_ENGINE_PENTESTAGENT_URL", "http://127.0.0.1:9999"
    )
    pa = PentestAgentAdapter()
    assert pa.status() == "unavailable"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9999",
        "http://127.1:9999",
        "http://0.0.0.0:9999",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "http://[::1]:8080",
        "http://localhost:8080",
        "http://user:pass@engine-pentestagent:8080",
        "https://engine-pentestagent:8080",
        "http://2130706433:8080",
    ],
)
def test_high2_engine_url_ssrf_rejected(monkeypatch, url):
    """AppSec HIGH-2: denylist-only loopback is insufficient — allowlist + IP checks."""
    monkeypatch.setenv("PENTEST_ENGINE_URL_ALLOWLIST", "engine-pentestagent")
    assert assert_allowed_engine_url(url) is not None


def test_high2_engine_url_allowlisted_compose_host(monkeypatch):
    monkeypatch.setenv("PENTEST_ENGINE_URL_ALLOWLIST", "engine-pentestagent")
    assert (
        assert_allowed_engine_url("http://engine-pentestagent:8080") is None
    )


def test_high2_engine_url_empty_allowlist_fail_closed(monkeypatch):
    monkeypatch.delenv("PENTEST_ENGINE_URL_ALLOWLIST", raising=False)
    assert (
        assert_allowed_engine_url("http://engine-pentestagent:8080") is not None
    )


@pytest.mark.asyncio
async def test_high2_non_allowlisted_url_marks_adapter_unavailable(monkeypatch):
    monkeypatch.setenv("PENTEST_ENGINE_MOCK", "0")
    monkeypatch.setenv("PENTEST_ENGINE_URL_ALLOWLIST", "engine-pentestagent")
    monkeypatch.setenv(
        "PENTEST_ENGINE_PENTESTAGENT_URL", "http://169.254.169.254/"
    )
    assert PentestAgentAdapter().status() == "unavailable"


@pytest.mark.asyncio
async def test_high2_allowlisted_url_ready_when_not_mock(monkeypatch):
    monkeypatch.setenv("PENTEST_ENGINE_MOCK", "0")
    monkeypatch.setenv("PENTEST_ENGINE_URL_ALLOWLIST", "engine-pentestagent")
    monkeypatch.setenv(
        "PENTEST_ENGINE_PENTESTAGENT_URL", "http://engine-pentestagent:8080"
    )
    assert PentestAgentAdapter().status() == "ready"


@pytest.mark.parametrize(
    ("env_key", "env_value"),
    [
        ("OLLAMA_HOST", "http://localhost:11434"),
        ("OLLAMA_HOST", "http://127.0.0.1:11434"),
        ("OLLAMA_BASE_URL", "http://ollama:11434"),
        ("LITELLM_BASE_URL", "http://localhost:11434"),
        ("LITELLM_BASE_URL", "http://127.0.0.1:11434"),
        ("PENTEST_ENGINE_LLM_BASE_URL", "http://127.1:11434"),
        ("OPENAI_API_BASE", "http://my-ollama-box:8080/v1"),
    ],
)
@pytest.mark.asyncio
async def test_high3_ollama_self_hosted_rejected(monkeypatch, env_key, env_value):
    """AppSec HIGH-3: localhost:11434 and OLLAMA_* must be typed-reject."""
    monkeypatch.setenv(env_key, env_value)
    assert assert_no_ollama_llm() is not None

    body = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="recon",
            targets=["https://example.com"],
        )
    )
    assert body["ok"] is False
    assert body["error"] == "self_hosted_llm_forbidden"


@pytest.mark.asyncio
async def test_high3_enterprise_litellm_allowed(monkeypatch):
    monkeypatch.setenv(
        "LITELLM_BASE_URL", "https://litellm.heimdallsec.example/v1"
    )
    assert assert_no_ollama_llm() is None
