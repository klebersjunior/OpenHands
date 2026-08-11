"""Typed stub client for mcp-engine tools (PROJETOSIN-197 contract).

Until 197 merges, this in-process stub satisfies orchestrator unit tests.
Replace implementation with stdio/HTTP MCP wrapper without changing call sites.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

EngineRunStatus = Literal[
    "queued",
    "running",
    "awaiting_confirmation",
    "succeeded",
    "failed",
    "cancelled",
]

CANONICAL_PHASES = ("recon", "scan", "analyze", "exploit")
PHASE_ALIASES = {
    "enumeration": "scan",
    "exploitation": "exploit",
}


@dataclass
class EngineRun:
    run_id: str
    engine_id: str
    phase: str
    status: EngineRunStatus
    summary: str | None = None
    finding_ids: list[str] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class EngineStartResult:
    ok: bool
    run: EngineRun | None = None
    error_code: str | None = None
    error_message: str | None = None
    confirmation_required: bool = False


class EngineClient:
    """In-memory fake for `engine_*` tools (197)."""

    def __init__(self) -> None:
        self._runs: dict[str, EngineRun] = {}
        self.cancelled_ids: list[str] = []
        # Tests / ops can flip this when mcp-network (198) is registered.
        self.network_server_available: bool = (
            os.environ.get("PENTEST_MCP_NETWORK_AVAILABLE", "").strip() == "1"
        )
        self.mobile_server_available: bool = (
            os.environ.get("PENTEST_MCP_MOBILE_AVAILABLE", "1").strip() != "0"
        )
        # When set, next start_phase for matching target fails with scope_violation.
        self.force_scope_violation_targets: set[str] = set()

    def normalize_phase(self, phase: str) -> str:
        key = phase.strip().lower()
        return PHASE_ALIASES.get(key, key)

    def list_engines(self) -> dict[str, Any]:
        engines = [
            {
                "id": "pentestagent",
                "status": "ready",
                "capabilities": ["recon", "scan", "analyze", "exploit"],
            }
        ]
        if os.environ.get("PENTEST_ENGINE_CAI_ENABLED", "").strip() == "true":
            engines.append(
                {
                    "id": "cai",
                    "status": "ready",
                    "capabilities": ["recon", "scan", "analyze", "exploit"],
                }
            )
        return {"engines": engines}

    def list_playbooks(self, engine_id: str | None = None) -> dict[str, Any]:
        del engine_id  # stub ignores filter; real MCP will honor it
        return {
            "playbooks": [
                {
                    "id": "web-blackbox-recon",
                    "title": "Engine stub web blackbox recon",
                    "phases": ["recon", "scan"],
                    "domains": ["web"],
                    "engine_id": "pentestagent",
                }
            ]
        }

    def start_phase(
        self,
        *,
        engine_id: str,
        phase: str,
        playbook_id: str | None = None,
        targets: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> EngineStartResult:
        del playbook_id, options
        if engine_id not in ("pentestagent", "cai"):
            return EngineStartResult(
                ok=False,
                error_code="invalid_engine",
                error_message=f"Unknown engine_id={engine_id}",
            )
        if engine_id == "cai" and os.environ.get(
            "PENTEST_ENGINE_CAI_ENABLED", ""
        ).strip() != "true":
            return EngineStartResult(
                ok=False,
                error_code="engine_not_enabled",
                error_message="CAI engine disabled",
            )
        normalized = self.normalize_phase(phase)
        if normalized not in CANONICAL_PHASES:
            return EngineStartResult(
                ok=False,
                error_code="invalid_phase",
                error_message=f"Invalid phase={phase}",
            )
        for target in targets or []:
            if target in self.force_scope_violation_targets:
                return EngineStartResult(
                    ok=False,
                    error_code="scope_violation",
                    error_message=f"Target out of scope: {target}",
                )
        run_id = str(uuid.uuid4())
        run = EngineRun(
            run_id=run_id,
            engine_id=engine_id,
            phase=normalized,
            status="succeeded",
            summary=f"stub:{normalized}",
            finding_ids=[],
        )
        self._runs[run_id] = run
        return EngineStartResult(ok=True, run=run)

    def get_run(self, run_id: str) -> EngineRun | None:
        return self._runs.get(run_id)

    def cancel_run(self, run_id: str) -> dict[str, Any]:
        self.cancelled_ids.append(run_id)
        run = self._runs.get(run_id)
        if run is not None:
            run.status = "cancelled"
        return {"ok": True}

    def domain_server_available(self, domain: str) -> bool:
        if domain == "network":
            return self.network_server_available
        if domain == "mobile":
            return self.mobile_server_available
        return True


# Process-wide default used by OrchestratorService unless overridden in tests.
_default_client = EngineClient()


def get_engine_client() -> EngineClient:
    return _default_client


def reset_engine_client() -> EngineClient:
    """Test helper — replace singleton with a fresh stub."""
    global _default_client
    _default_client = EngineClient()
    return _default_client
