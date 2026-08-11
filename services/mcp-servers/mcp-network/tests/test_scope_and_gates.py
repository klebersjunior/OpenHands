"""AC-198-1 / AC-198-2 — scope fail-closed + confirmation gates."""

from __future__ import annotations

import json

import pytest

from shared.confirmation import ACTIVE_TOOLS, approve_confirmation
from shared.findings_client import FindingsClient
from tests.conftest import ENGAGEMENT_ID, FakeFindingsTransport


@pytest.mark.asyncio
async def test_ac_198_1_out_of_scope_all_mutating_tools():
    from tools.gvm_scan import run_gvm_start_scan
    from tools.msf_rpc import run_msf_rpc_execute
    from tools.nmap_scan import run_nmap_scan

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    nmap = json.loads(
        await run_nmap_scan(
            targets=["evil.example.org"],
            engagement_id=ENGAGEMENT_ID,
            profile="safe",
            findings=client,
        )
    )
    assert nmap["ok"] is False
    assert nmap["error"] == "scope_violation"

    gvm = json.loads(
        await run_gvm_start_scan(
            targets=["evil.example.org"],
            engagement_id=ENGAGEMENT_ID,
        )
    )
    assert gvm["ok"] is False
    assert gvm["error"] == "scope_violation"

    msf = json.loads(
        await run_msf_rpc_execute(
            module="auxiliary/scanner/portscan/tcp",
            options={"RHOSTS": "evil.example.org"},
            engagement_id=ENGAGEMENT_ID,
        )
    )
    assert msf["ok"] is False
    assert msf["error"] == "scope_violation"
    assert transport.posts == []


@pytest.mark.asyncio
async def test_ac_198_1_empty_allowlist_fail_closed(monkeypatch):
    monkeypatch.delenv("PENTEST_SCOPE_ALLOWLIST", raising=False)
    from tools.nmap_scan import run_nmap_scan

    body = json.loads(
        await run_nmap_scan(
            targets=["10.0.0.5"],
            engagement_id=ENGAGEMENT_ID,
            profile="discovery",
        )
    )
    assert body["ok"] is False
    assert body["error"] == "scope_violation"


@pytest.mark.asyncio
async def test_ac_198_2_nmap_full_requires_confirmation():
    from tools.nmap_scan import run_nmap_scan

    assert "net_nmap_scan" in ACTIVE_TOOLS
    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    first = json.loads(
        await run_nmap_scan(
            targets=["10.0.0.5"],
            engagement_id=ENGAGEMENT_ID,
            profile="full",
            findings=client,
        )
    )
    assert first["ok"] is False
    assert first["error"] == "confirmation_required"
    assert first["request_id"]
    assert transport.posts == []

    token = approve_confirmation(first["request_id"])
    second = json.loads(
        await run_nmap_scan(
            targets=["10.0.0.5"],
            engagement_id=ENGAGEMENT_ID,
            profile="full",
            confirmation_token=token,
            findings=client,
        )
    )
    assert second["ok"] is True
    assert len(transport.posts) >= 1


@pytest.mark.asyncio
async def test_nmap_discovery_skips_confirmation():
    from tools.nmap_scan import run_nmap_scan

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)
    body = json.loads(
        await run_nmap_scan(
            targets=["target.lab.local"],
            engagement_id=ENGAGEMENT_ID,
            profile="discovery",
            findings=client,
        )
    )
    assert body["ok"] is True
    assert "confirmation_required" not in body


@pytest.mark.asyncio
async def test_gvm_and_msf_require_confirmation_in_semi():
    from tools.gvm_scan import run_gvm_start_scan
    from tools.msf_rpc import run_msf_rpc_execute

    gvm = json.loads(
        await run_gvm_start_scan(
            targets=["10.0.0.5"],
            engagement_id=ENGAGEMENT_ID,
        )
    )
    assert gvm["error"] == "confirmation_required"

    msf = json.loads(
        await run_msf_rpc_execute(
            module="auxiliary/scanner/portscan/tcp",
            options={"RHOSTS": "10.0.0.5"},
            engagement_id=ENGAGEMENT_ID,
        )
    )
    assert msf["error"] == "confirmation_required"


@pytest.mark.asyncio
async def test_msf_sessions_redact_credentials():
    from tools.msf_rpc import run_msf_session_list

    body = json.loads(await run_msf_session_list(engagement_id=ENGAGEMENT_ID))
    assert body["ok"] is True
    sessions = body["sessions"]
    assert sessions
    assert sessions[0].get("password") == "[REDACTED]"
