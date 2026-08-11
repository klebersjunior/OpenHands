"""engine_get_run — poll run status."""

from __future__ import annotations

from adapters.base import get_run_registry
from shared.tool_result import err, ok


async def run_get_run(*, run_id: str) -> str:
    run = get_run_registry().get(run_id)
    if run is None:
        return err("invalid_run", run_id=run_id, message="Unknown run_id")
    return ok(
        {
            "run_id": run.run_id,
            "engine_id": run.engine_id,
            "phase": run.phase,
            "status": run.status,
            "summary": run.summary,
            "finding_ids": list(run.finding_ids),
        }
    )
