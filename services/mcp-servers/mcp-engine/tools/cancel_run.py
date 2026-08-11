"""engine_cancel_run — best-effort cancel."""

from __future__ import annotations

from adapters import get_adapters
from adapters.base import emit_run_event, get_run_registry
from shared.tool_result import err, ok


async def run_cancel_run(*, run_id: str) -> str:
    registry = get_run_registry()
    run = registry.get(run_id)
    if run is None:
        return err("invalid_run", run_id=run_id, message="Unknown run_id")

    adapters = get_adapters()
    adapter = adapters.get(run.engine_id)
    if adapter is not None:
        run = await adapter.cancel(run)
    else:
        run.status = "cancelled"
        emit_run_event(run)
    registry.put(run)
    return ok({"run_id": run.run_id, "status": run.status})
