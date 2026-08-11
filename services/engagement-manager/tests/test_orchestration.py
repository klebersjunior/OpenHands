"""AC-196-1..5,7 — orchestration playbooks (PROJETOSIN-196)."""

from __future__ import annotations

import pytest

from app.services.orchestrator.engine_client import reset_engine_client
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _fresh_engine():
    reset_engine_client()
    yield
    reset_engine_client()


async def _create_engagement(client, *, autonomy_mode: str = "semi_autonomous") -> str:
    resp = await client.post(
        "/api/pentest/engagements",
        json={
            "name": "orch-test",
            "client_name": "ACME",
            "runtime_profile": "web",
            "autonomy_mode": autonomy_mode,
        },
        headers=auth_headers(),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _authorize_scope(client, eng_id: str, domain: str = "example.com") -> None:
    resp = await client.post(
        f"/api/pentest/engagements/{eng_id}/scope",
        json={
            "rule_type": "allow",
            "target_type": "domain",
            "target_value": domain,
        },
        headers=auth_headers("admin"),
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_ac196_5_catalog_lists_mvp_playbooks(client):
    """AC-196-5: GET catalog lists MVP playbooks."""
    eng_id = await _create_engagement(client)
    resp = await client.get(
        f"/api/pentest/engagements/{eng_id}/orchestration/playbooks",
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    ids = {p["id"] for p in resp.json()["playbooks"]}
    assert "web-passive-mvp" in ids
    assert "network-discovery-mvp" in ids
    assert "mobile-static-mvp" in ids


@pytest.mark.asyncio
async def test_ac196_1_create_run_persists_steps(client):
    """AC-196-1: POST /runs creates run and persists steps."""
    eng_id = await _create_engagement(client)
    await _authorize_scope(client, eng_id)

    created = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs",
        json={"playbook_id": "web-passive-mvp", "targets": ["example.com"]},
        headers=auth_headers(),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["run_id"]
    assert body["status"] in (
        "pending",
        "running",
        "awaiting_confirmation",
        "succeeded",
    )

    detail = await client.get(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs/{body['run_id']}",
        headers=auth_headers(),
    )
    assert detail.status_code == 200
    steps = detail.json()["steps"]
    assert len(steps) == 4
    assert [s["phase_id"] for s in steps] == [
        "recon",
        "scan",
        "analyze",
        "exploit",
    ]


@pytest.mark.asyncio
async def test_ac196_2_confirmation_gate_semi_no_exploit(client):
    """AC-196-2: confirmation gate in semi → awaiting_confirmation, no exploit call."""
    eng_id = await _create_engagement(client, autonomy_mode="semi_autonomous")
    await _authorize_scope(client, eng_id)
    engine = reset_engine_client()

    created = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs",
        json={"playbook_id": "web-passive-mvp", "targets": ["example.com"]},
        headers=auth_headers(),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "awaiting_confirmation"

    detail = await client.get(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs/{created.json()['run_id']}",
        headers=auth_headers(),
    )
    data = detail.json()
    exploit = next(s for s in data["steps"] if s["phase_id"] == "exploit")
    assert exploit["status"] == "awaiting_confirmation"
    assert exploit["engine_run_id"] is None
    # Engine stub only ran pre-exploit phases
    phases = {r.phase for r in engine._runs.values()}
    assert "exploit" not in phases
    assert {"recon", "scan", "analyze"} <= phases


@pytest.mark.asyncio
async def test_ac196_3_scope_violation_fails_step(client):
    """AC-196-3: allowlist violation → step failed scope_violation; no silent advance."""
    eng_id = await _create_engagement(client)
    await _authorize_scope(client, eng_id, domain="example.com")

    created = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs",
        json={
            "playbook_id": "web-passive-mvp",
            "targets": ["evil.out-of-scope.test"],
        },
        headers=auth_headers(),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "failed"

    detail = await client.get(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs/{created.json()['run_id']}",
        headers=auth_headers(),
    )
    data = detail.json()
    assert data["error_code"] == "scope_violation"
    failed_steps = [s for s in data["steps"] if s["status"] == "failed"]
    assert failed_steps
    assert failed_steps[0]["error_code"] == "scope_violation"
    # Later phases must not have succeeded
    assert all(
        s["status"] != "succeeded"
        for s in data["steps"]
        if s["sequence"] > failed_steps[0]["sequence"]
    )


@pytest.mark.asyncio
async def test_ac196_4_cancel_propagates_to_engine(client):
    """AC-196-4: cancel marks run cancelled and propagates to engine stub."""
    eng_id = await _create_engagement(client)
    await _authorize_scope(client, eng_id)
    engine = reset_engine_client()

    created = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs",
        json={"playbook_id": "web-passive-mvp", "targets": ["example.com"]},
        headers=auth_headers(),
    )
    run_id = created.json()["run_id"]
    assert created.json()["status"] == "awaiting_confirmation"
    assert engine._runs  # prior phases started

    cancelled = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs/{run_id}/cancel",
        headers=auth_headers(),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert engine.cancelled_ids
    assert set(engine.cancelled_ids) == set(engine._runs.keys())


@pytest.mark.asyncio
async def test_ac196_7_no_exploit_capability_blocks_phase(client, monkeypatch):
    """AC-196-7: without exploit capability, exploit phase is not started."""
    from shared import capabilities as caps

    monkeypatch.setitem(
        caps.PROFILE_CAPABILITIES,
        "pentester",
        [
            c
            for c in caps.PROFILE_CAPABILITIES["pentester"]
            if c != "pentest.exploit.active"
        ],
    )

    eng_id = await _create_engagement(client, autonomy_mode="autonomous")
    await _authorize_scope(client, eng_id)
    engine = reset_engine_client()

    created = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs",
        json={"playbook_id": "web-passive-mvp", "targets": ["example.com"]},
        headers=auth_headers(),
    )
    assert created.status_code == 201
    detail = await client.get(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs/{created.json()['run_id']}",
        headers=auth_headers(),
    )
    data = detail.json()
    exploit = next(s for s in data["steps"] if s["phase_id"] == "exploit")
    assert exploit["status"] == "blocked_capability"
    assert exploit["error_code"] == "capability_denied"
    assert exploit["engine_run_id"] is None
    assert "exploit" not in {r.phase for r in engine._runs.values()}


@pytest.mark.asyncio
async def test_playbook_id_path_traversal_rejected(client):
    eng_id = await _create_engagement(client)
    resp = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs",
        json={"playbook_id": "../etc/passwd"},
        headers=auth_headers(),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_autonomy_mode_in_body_ignored(client):
    """Body autonomy_mode must not bypass engagement semi gate."""
    eng_id = await _create_engagement(client, autonomy_mode="semi_autonomous")
    await _authorize_scope(client, eng_id)

    created = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs",
        json={
            "playbook_id": "web-passive-mvp",
            "targets": ["example.com"],
            "autonomy_mode": "autonomous",
        },
        headers=auth_headers(),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "awaiting_confirmation"


@pytest.mark.asyncio
async def test_view_only_cannot_start_run(client):
    eng_id = await _create_engagement(client)
    resp = await client.post(
        f"/api/pentest/engagements/{eng_id}/orchestration/runs",
        json={"playbook_id": "web-passive-mvp"},
        headers=auth_headers("client"),
    )
    assert resp.status_code == 403
