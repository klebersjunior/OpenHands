"""AC-197-2 / AC-197-3 — scope fail-closed and exploit confirmation gate."""

from __future__ import annotations

import json

import pytest

from shared.confirmation import approve_confirmation
from shared.findings_client import FindingsClient
from tests.conftest import FakeFindingsTransport


@pytest.mark.asyncio
async def test_ac_197_2_scope_violation_no_spawn():
    from tools.start_phase import run_start_phase

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    body = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="scan",
            targets=["https://evil.out-of-scope.test"],
            findings=client,
        )
    )
    assert body["ok"] is False
    assert body["error"] == "scope_violation"
    assert transport.posts == []


@pytest.mark.asyncio
async def test_ac_197_2_empty_allowlist_fail_closed(monkeypatch):
    monkeypatch.setenv("PENTEST_SCOPE_ALLOWLIST", "")
    from tools.start_phase import run_start_phase

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)
    body = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="recon",
            targets=["https://example.com"],
            findings=client,
        )
    )
    assert body["ok"] is False
    assert body["error"] == "scope_violation"
    assert transport.posts == []


@pytest.mark.asyncio
async def test_ac_197_3_exploit_semi_without_token_confirmation_required():
    from tools.start_phase import run_start_phase

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    body = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="exploit",
            targets=["https://example.com"],
            findings=client,
        )
    )
    assert body["ok"] is False
    assert body["error"] == "confirmation_required"
    assert body["request_id"]
    assert transport.posts == []


@pytest.mark.asyncio
async def test_ac_197_3_exploit_with_token_proceeds():
    from tools.start_phase import run_start_phase

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    first = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="exploit",
            targets=["https://example.com"],
            findings=client,
        )
    )
    token = approve_confirmation(first["request_id"])
    second = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="exploit",
            targets=["https://example.com"],
            confirmation_token=token,
            findings=client,
        )
    )
    assert second["ok"] is True
    assert second["status"] == "succeeded"
    assert len(transport.posts) >= 1


@pytest.mark.asyncio
async def test_phase_aliases_enumeration_and_exploitation():
    from adapters.base import normalize_phase

    assert normalize_phase("enumeration") == "scan"
    assert normalize_phase("exploitation") == "exploit"


@pytest.mark.asyncio
async def test_autonomy_mode_in_options_rejected():
    from tools.start_phase import run_start_phase

    body = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="scan",
            targets=["https://example.com"],
            options={"autonomy_mode": "autonomous"},
        )
    )
    assert body["ok"] is False
    assert body["error"] == "invalid_options"


@pytest.mark.asyncio
async def test_cai_disabled_returns_engine_not_enabled():
    from tools.start_phase import run_start_phase

    body = json.loads(
        await run_start_phase(
            engine_id="cai",
            phase="recon",
            targets=["https://example.com"],
        )
    )
    assert body["ok"] is False
    assert body["error"] == "engine_not_enabled"


@pytest.mark.asyncio
async def test_capability_denied_for_exploit_without_cap(monkeypatch):
    monkeypatch.setenv("PENTEST_CAPABILITIES", "pentest.scan.passive")
    from tools.start_phase import run_start_phase

    body = json.loads(
        await run_start_phase(
            engine_id="pentestagent",
            phase="exploit",
            targets=["https://example.com"],
        )
    )
    assert body["ok"] is False
    assert body["error"] == "capability_denied"
