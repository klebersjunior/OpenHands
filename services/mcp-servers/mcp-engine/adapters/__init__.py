"""Engine adapters for mcp-engine (PROJETOSIN-197)."""

from __future__ import annotations

from adapters.base import EngineAdapter, RunRecord, RunRegistry, get_run_registry
from adapters.cai import CaiAdapter, cai_enabled
from adapters.pentestagent import PentestAgentAdapter

__all__ = [
    "CaiAdapter",
    "EngineAdapter",
    "PentestAgentAdapter",
    "RunRecord",
    "RunRegistry",
    "cai_enabled",
    "get_adapters",
    "get_run_registry",
]


def get_adapters() -> dict[str, EngineAdapter]:
    """Return enabled adapters keyed by engine_id."""
    adapters: dict[str, EngineAdapter] = {
        "pentestagent": PentestAgentAdapter(),
    }
    if cai_enabled():
        adapters["cai"] = CaiAdapter()
    return adapters
