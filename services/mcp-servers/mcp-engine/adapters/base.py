"""Engine adapter protocol and in-memory run registry (PROJETOSIN-197)."""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

RunStatus = Literal[
    "queued",
    "running",
    "awaiting_confirmation",
    "succeeded",
    "failed",
    "cancelled",
]

CanonicalPhase = Literal["recon", "scan", "analyze", "exploit"]

PHASE_ALIASES: dict[str, CanonicalPhase] = {
    "recon": "recon",
    "scan": "scan",
    "analyze": "analyze",
    "exploit": "exploit",
    "enumeration": "scan",
    "exploitation": "exploit",
}

ENGAGEMENT_ID_ENV = "ENGAGEMENT_ID"
CAPABILITIES_ENV = "PENTEST_CAPABILITIES"
CAP_SCAN_PASSIVE = "pentest.scan.passive"
CAP_EXPLOIT_ACTIVE = "pentest.exploit.active"


@dataclass
class RunRecord:
    run_id: str
    engine_id: str
    phase: CanonicalPhase
    status: RunStatus
    engagement_id: str
    targets: list[str] = field(default_factory=list)
    playbook_id: str | None = None
    summary: str | None = None
    finding_ids: list[str] = field(default_factory=list)
    error: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


class EngineAdapter(Protocol):
    engine_id: str
    capabilities: list[str]

    def status(self) -> str:
        """ready | unavailable | disabled."""
        ...

    async def start(
        self,
        *,
        run: RunRecord,
        registry: "RunRegistry",
    ) -> RunRecord:
        ...

    async def get(self, run: RunRecord) -> RunRecord:
        ...

    async def cancel(self, run: RunRecord) -> RunRecord:
        ...


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(
        self,
        *,
        engine_id: str,
        phase: CanonicalPhase,
        engagement_id: str,
        targets: list[str] | None = None,
        playbook_id: str | None = None,
        options: dict[str, Any] | None = None,
        status: RunStatus = "queued",
    ) -> RunRecord:
        run = RunRecord(
            run_id=str(uuid.uuid4()),
            engine_id=engine_id,
            phase=phase,
            status=status,
            engagement_id=engagement_id,
            targets=list(targets or []),
            playbook_id=playbook_id,
            options=dict(options or {}),
        )
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def put(self, run: RunRecord) -> RunRecord:
        self._runs[run.run_id] = run
        return run


_REGISTRY = RunRegistry()


def get_run_registry() -> RunRegistry:
    return _REGISTRY


def reset_run_registry() -> None:
    """Test helper — clear in-memory runs."""
    global _REGISTRY
    _REGISTRY = RunRegistry()


def normalize_phase(phase: str) -> CanonicalPhase | None:
    key = (phase or "").strip().lower()
    return PHASE_ALIASES.get(key)


def engagement_id_from_env() -> str:
    return os.environ.get(ENGAGEMENT_ID_ENV, "").strip()


def configured_capabilities() -> set[str] | None:
    """
    Optional launcher-injected capabilities (CSV).

    ``None`` means the launcher did not pass context — attach gating is
    documented as the caller's responsibility; tools do not invent RBAC.
    """
    raw = os.environ.get(CAPABILITIES_ENV)
    if raw is None:
        return None
    return {part.strip() for part in raw.split(",") if part.strip()}


def emit_run_event(run: RunRecord) -> None:
    """Structured JSON log for PROJETOSIN-199 (no secrets / prompts)."""
    payload = {
        "event": "engine.run",
        "engagement_id": run.engagement_id,
        "run_id": run.run_id,
        "engine_id": run.engine_id,
        "phase": run.phase,
        "status": run.status,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload, default=str), file=sys.stdout, flush=True)


def assert_no_ollama_llm() -> str | None:
    """Refuse engine LLM base URLs that point at Ollama/self-hosted local."""
    for key in (
        "PENTEST_ENGINE_LLM_BASE_URL",
        "LITELLM_BASE_URL",
        "OPENAI_API_BASE",
        "OLLAMA_HOST",
        "OLLAMA_BASE_URL",
    ):
        value = os.environ.get(key, "").strip().lower()
        if not value:
            continue
        if "ollama" in value or value.startswith("http://127.0.0.1:11434"):
            return f"{key} must not point at Ollama/self-hosted LLM"
    return None
