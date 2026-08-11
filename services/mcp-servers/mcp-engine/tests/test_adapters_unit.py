"""AC-197-4 / AC-197-6 — adapter unit tests without real Docker images."""

from __future__ import annotations

import json

import pytest

from adapters.base import RunRegistry, assert_no_ollama_llm
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
    monkeypatch.setenv(
        "PENTEST_ENGINE_PENTESTAGENT_URL", "http://127.0.0.1:9999"
    )
    pa = PentestAgentAdapter()
    assert pa.status() == "unavailable"


@pytest.mark.asyncio
async def test_ollama_llm_rejected(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    assert assert_no_ollama_llm() is not None

    body = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="recon",
            targets=["https://example.com"],
        )
    )
    assert body["ok"] is False
    assert body["error"] == "engine_unavailable"
