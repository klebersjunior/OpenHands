"""AC-197-1 / AC-197-5 — engine_* tool contract."""

from __future__ import annotations

import inspect
import json

import pytest

from shared.findings_client import FindingsClient
from tests.conftest import FakeFindingsTransport


@pytest.mark.asyncio
async def test_ac_197_1_list_engines_pentestagent_cai_absent_when_flag_off():
    from tools.list_engines import run_list_engines

    body = json.loads(await run_list_engines())
    assert body["ok"] is True
    ids = {e["id"] for e in body["engines"]}
    assert "pentestagent" in ids
    assert "cai" not in ids
    pa = next(e for e in body["engines"] if e["id"] == "pentestagent")
    assert "pentest.scan.passive" in pa["capabilities"]
    assert pa["status"] == "ready"


@pytest.mark.asyncio
async def test_ac_197_1_cai_listed_when_enabled(monkeypatch):
    monkeypatch.setenv("PENTEST_ENGINE_CAI_ENABLED", "true")
    from tools.list_engines import run_list_engines

    body = json.loads(await run_list_engines())
    ids = {e["id"] for e in body["engines"]}
    assert "pentestagent" in ids
    assert "cai" in ids


@pytest.mark.asyncio
async def test_ac_197_5_schema_stable_across_engines(monkeypatch):
    """Troca engine_id não muda schema das tools."""
    from server import mcp

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        "engine_list_engines",
        "engine_start_phase",
        "engine_get_run",
        "engine_cancel_run",
        "engine_list_playbooks",
    }
    assert expected == names

    by_name = {t.name: t for t in tools}
    start_props = (by_name["engine_start_phase"].inputSchema or {}).get(
        "properties"
    ) or {}
    assert "engine_id" in start_props
    assert "phase" in start_props
    assert "autonomy_mode" not in start_props

    monkeypatch.setenv("PENTEST_ENGINE_CAI_ENABLED", "true")
    tools_on = await mcp.list_tools()
    start_on = next(t for t in tools_on if t.name == "engine_start_phase")
    props_on = (start_on.inputSchema or {}).get("properties") or {}
    assert set(props_on) == set(start_props)


@pytest.mark.asyncio
async def test_ac_197_5_start_schema_same_for_cai_and_pentestagent(monkeypatch):
    monkeypatch.setenv("PENTEST_ENGINE_CAI_ENABLED", "true")
    from tools.start_phase import run_start_phase

    transport = FakeFindingsTransport()
    client = FindingsClient(base_url="http://findings.test", transport=transport)

    for engine_id in ("pentestagent", "cai"):
        body = json.loads(
            await run_start_phase(
                engine_id=engine_id,
                phase="recon",
                targets=["https://example.com"],
                findings=client,
            )
        )
        assert body["ok"] is True
        assert "run_id" in body
        assert "status" in body
        assert set(body.keys()) >= {"ok", "run_id", "status"}


@pytest.mark.asyncio
async def test_mcp_tools_omit_autonomy_mode_arg():
    from tools.start_phase import run_start_phase

    assert "autonomy_mode" not in inspect.signature(run_start_phase).parameters


@pytest.mark.asyncio
async def test_list_playbooks_mvp_catalog():
    from tools.list_playbooks import run_list_playbooks

    body = json.loads(await run_list_playbooks())
    assert body["ok"] is True
    ids = {p["id"] for p in body["playbooks"]}
    assert "web-blackbox-recon" in ids
    assert "web-scan-passive" in ids
    for pb in body["playbooks"]:
        assert "phases" in pb
        assert "domains" in pb
        assert "title" in pb
