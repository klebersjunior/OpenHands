"""Custody / observability hooks for orchestration transitions (PROJETOSIN-199).

No-op until 199 helpers merge — emit structured log only, never secrets.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("engagement_manager.orchestrator.custody")


def emit_engine_run_event(
    *,
    engagement_id: str,
    run_id: str,
    engine_id: str,
    phase: str,
    status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "event": "pentest.engine.run",
        "engagement_id": engagement_id,
        "run_id": run_id,
        "engine_id": engine_id,
        "phase": phase,
        "status": status,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        # Never attach secrets / full prompts.
        safe = {
            k: v
            for k, v in extra.items()
            if k
            not in (
                "api_key",
                "token",
                "password",
                "secret",
                "prompt",
                "session_api_key",
            )
        }
        payload.update(safe)
    logger.info("custody %s", json.dumps(payload, default=str))
