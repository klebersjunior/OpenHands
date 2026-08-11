"""CAI engine adapter — opt-in via PENTEST_ENGINE_CAI_ENABLED (PROJETOSIN-197)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx

from adapters.base import RunRecord, RunRegistry, emit_run_event
from shared.findings_client import FindingsClient
from shared.normalize import normalize_finding

ENGINE_ID = "cai"
CAPABILITIES = ["pentest.scan.passive", "pentest.exploit.active"]

CAI_ENABLED_ENV = "PENTEST_ENGINE_CAI_ENABLED"
CAI_URL_ENV = "PENTEST_ENGINE_CAI_URL"
MOCK_ENV = "PENTEST_ENGINE_MOCK"
AUTONOMY_MODE_ENV = "PENTEST_AUTONOMY_MODE"


def cai_enabled() -> bool:
    return os.environ.get(CAI_ENABLED_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _mock_mode() -> bool:
    raw = os.environ.get(MOCK_ENV)
    if raw is not None:
        return raw.strip().lower() in ("1", "true", "yes")
    return not os.environ.get(CAI_URL_ENV, "").strip()


def _is_loopback_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ("127.0.0.1", "localhost", "::1")


class CaiAdapter:
    engine_id = ENGINE_ID
    capabilities = list(CAPABILITIES)

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        findings: FindingsClient | None = None,
    ):
        self._transport = transport
        self._findings = findings

    def status(self) -> str:
        if not cai_enabled():
            return "disabled"
        if _mock_mode():
            return "ready"
        url = os.environ.get(CAI_URL_ENV, "").strip()
        if not url:
            return "unavailable"
        if _is_loopback_url(url):
            return "unavailable"
        return "ready"

    async def start(
        self,
        *,
        run: RunRecord,
        registry: RunRegistry,
    ) -> RunRecord:
        if not cai_enabled():
            run.status = "failed"
            run.error = "engine_not_enabled"
            registry.put(run)
            emit_run_event(run)
            return run
        if self.status() != "ready":
            run.status = "failed"
            run.error = "engine_unavailable"
            registry.put(run)
            emit_run_event(run)
            return run

        run.status = "running"
        registry.put(run)
        emit_run_event(run)

        if _mock_mode() or self._transport is not None:
            return await self._run_mock(run, registry)

        return await self._run_remote(run, registry)

    async def get(self, run: RunRecord) -> RunRecord:
        return run

    async def cancel(self, run: RunRecord) -> RunRecord:
        if run.status in ("succeeded", "failed", "cancelled"):
            return run
        run.status = "cancelled"
        emit_run_event(run)
        return run

    async def _run_mock(self, run: RunRecord, registry: RunRegistry) -> RunRecord:
        client = self._findings or FindingsClient(transport=self._transport)
        finding_ids: list[str] = []
        for item in self._stub_findings(run):
            payload = normalize_finding(
                engagement_id=run.engagement_id,
                source_tool=ENGINE_ID,
                title=item["title"],
                severity=item["severity"],
                asset=item.get("asset"),
                endpoint=item.get("endpoint"),
                evidence=item.get("evidence"),
                description=f"CAI phase={run.phase}",
                tags=["engine", ENGINE_ID, run.phase],
            )
            posted = await client.post_finding(payload)
            finding = posted.get("finding") or {}
            fid = finding.get("id") or posted.get("existing_finding_id")
            if fid:
                finding_ids.append(str(fid))

        run.finding_ids = finding_ids
        run.summary = f"cai {run.phase} completed ({len(finding_ids)} findings)"
        run.status = "succeeded"
        registry.put(run)
        emit_run_event(run)
        return run

    async def _run_remote(self, run: RunRecord, registry: RunRegistry) -> RunRecord:
        url = os.environ.get(CAI_URL_ENV, "").rstrip("/")
        if not url or _is_loopback_url(url):
            run.status = "failed"
            run.error = "engine_unavailable"
            registry.put(run)
            emit_run_event(run)
            return run

        autonomy = os.environ.get(AUTONOMY_MODE_ENV, "semi_autonomous")
        body = {
            "run_id": run.run_id,
            "phase": run.phase,
            "targets": run.targets,
            "playbook_id": run.playbook_id,
            "options": run.options,
            "autonomy_mode": autonomy,
            "engagement_id": run.engagement_id,
        }
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=60.0
            ) as client:
                resp = await client.post(f"{url}/v1/phases/start", json=body)
            if resp.status_code >= 400:
                run.status = "failed"
                run.error = "engine_unavailable"
            else:
                data = resp.json() if resp.content else {}
                run.status = data.get("status", "running")
                run.summary = data.get("summary")
                run.finding_ids = list(data.get("finding_ids") or [])
        except httpx.HTTPError:
            run.status = "failed"
            run.error = "engine_unavailable"
        registry.put(run)
        emit_run_event(run)
        return run

    def _stub_findings(self, run: RunRecord) -> list[dict[str, Any]]:
        asset = run.targets[0] if run.targets else "unknown"
        return [
            {
                "title": f"CAI {run.phase}: informational finding",
                "severity": "info",
                "asset": asset,
                "endpoint": "/",
                "evidence": {"phase": run.phase, "engine": ENGINE_ID},
            }
        ]
