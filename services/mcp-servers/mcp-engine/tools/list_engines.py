"""engine_list_engines — list available offensive engines."""

from __future__ import annotations

from adapters import get_adapters
from shared.tool_result import ok


async def run_list_engines() -> str:
    """CAI is omitted entirely when PENTEST_ENGINE_CAI_ENABLED is off (AC-197-1)."""
    engines = [
        {
            "id": engine_id,
            "status": adapter.status(),
            "capabilities": list(adapter.capabilities),
        }
        for engine_id, adapter in get_adapters().items()
    ]
    return ok({"engines": engines})
