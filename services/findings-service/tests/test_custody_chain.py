"""AC-199-3/5 — custody API + finding.mutate span."""

from __future__ import annotations

import uuid

import pytest

from shared.custody import verify_chain
from shared.otel_setup import EVENT_FINDING_MUTATE, attach_inmemory_exporter

# auth_headers comes from conftest (pytest plugin path)
from conftest import auth_headers


@pytest.mark.asyncio
async def test_ac_199_3_custody_api_chain(client):
    eng = uuid.uuid4()
    # Append three links via internal API
    hashes = []
    for i, action in enumerate(("a", "b", "c")):
        resp = await client.post(
            "/internal/custody",
            headers=auth_headers(),
            json={
                "engagement_id": str(eng),
                "actor": "session:test",
                "action": action,
                "resource_type": "evidence",
                "resource_id": f"ref-{i}",
                "metadata": {"path": f"s3://eng/{i}.bin", "Authorization": "secret"},
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        hashes.append(body["hash"])
        assert body["metadata_redacted"]["Authorization"] == "[REDACTED]"
        assert "secret" not in resp.text

    listed = await client.get(
        f"/api/pentest/engagements/{eng}/custody",
        headers=auth_headers(),
    )
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert listed.json()["total"] == 3
    assert verify_chain(items) is True

    # Tamper middle hash in a reconstructed chain view
    items[1]["action"] = "TAMPERED"
    assert verify_chain(items) is False


@pytest.mark.asyncio
async def test_ac_199_5_finding_create_emits_mutate_span(client):
    exporter = attach_inmemory_exporter()
    eng = uuid.uuid4()
    resp = await client.post(
        "/api/pentest/findings",
        headers=auth_headers(),
        json={
            "engagement_id": str(eng),
            "source_tool": "nuclei",
            "title": "Open redirect",
            "severity": "medium",
            "asset": "app.example.com",
            "endpoint": "https://app.example.com/r",
        },
    )
    assert resp.status_code == 201, resp.text
    finding_id = resp.json()["id"]

    spans = exporter.get_finished_spans()
    mutate = [s for s in spans if s.name == EVENT_FINDING_MUTATE]
    assert mutate, f"expected {EVENT_FINDING_MUTATE}, got {[s.name for s in spans]}"
    assert mutate[0].attributes.get("action") == "create"
    assert mutate[0].attributes.get("finding.id") == finding_id

    custody = await client.get(
        f"/api/pentest/engagements/{eng}/custody",
        headers=auth_headers(),
    )
    assert custody.status_code == 200
    assert custody.json()["total"] >= 1
