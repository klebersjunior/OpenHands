"""AC-198 — mcp-network tool contract + fixture findings."""

from __future__ import annotations

import inspect
import json

import pytest

from shared.findings_client import FindingsClient
from tests.conftest import ENGAGEMENT_ID, FakeFindingsTransport


@pytest.mark.asyncio
async def test_ac_198_tools_exposed():
    from server import mcp

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        "net_nmap_scan",
        "net_gvm_start_scan",
        "net_gvm_get_report",
        "net_msf_rpc_execute",
        "net_msf_session_list",
    }
    assert expected.issubset(names)
    for tool in tools:
        assert tool.inputSchema is not None
        assert tool.inputSchema.get("type") == "object"
        props = tool.inputSchema.get("properties") or {}
        assert "engagement_id" in props
        assert "autonomy_mode" not in props


@pytest.mark.asyncio
async def test_ac_198_4_nmap_fixture_posts_findings():
    from tools.nmap_scan import run_nmap_scan

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)
    body = json.loads(
        await run_nmap_scan(
            targets=["10.0.0.5"],
            engagement_id=ENGAGEMENT_ID,
            profile="discovery",
            findings=client,
        )
    )
    assert body["ok"] is True
    assert body["findings_count"] >= 1
    assert transport.posts
    assert all(p["source_tool"] == "nmap" for p in transport.posts)


@pytest.mark.asyncio
async def test_ac_198_4_gvm_fixture_normalize_and_post():
    from tools.gvm_report import run_gvm_get_report

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)
    body = json.loads(
        await run_gvm_get_report(
            scan_id="stub-scan-1",
            engagement_id=ENGAGEMENT_ID,
            findings=client,
        )
    )
    assert body["ok"] is True
    assert body["findings_count"] >= 1
    assert transport.posts
    assert all(p["source_tool"] == "openvas" for p in transport.posts)


@pytest.mark.asyncio
async def test_runners_omit_autonomy_mode_arg():
    from tools.gvm_scan import run_gvm_start_scan
    from tools.msf_rpc import run_msf_rpc_execute
    from tools.nmap_scan import run_nmap_scan

    for fn in (run_nmap_scan, run_gvm_start_scan, run_msf_rpc_execute):
        assert "autonomy_mode" not in inspect.signature(fn).parameters
