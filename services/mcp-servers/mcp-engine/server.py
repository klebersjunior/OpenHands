"""mcp-engine — stdio MCP server for offensive engines (PROJETOSIN-197)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from mcp.server.fastmcp import FastMCP

from tools.cancel_run import run_cancel_run
from tools.get_run import run_get_run
from tools.list_engines import run_list_engines
from tools.list_playbooks import run_list_playbooks
from tools.start_phase import run_start_phase

mcp = FastMCP("mcp-engine")


@mcp.tool()
async def engine_list_engines() -> str:
    """List available engines (pentestagent always; cai when enabled)."""
    return await run_list_engines()


@mcp.tool()
async def engine_start_phase(
    engine_id: str,
    phase: str,
    playbook_id: str | None = None,
    targets: list[str] | None = None,
    options: dict[str, Any] | None = None,
    confirmation_token: str | None = None,
) -> str:
    """Start a canonical engine phase (recon/scan/analyze/exploit).

    Autonomy comes from PENTEST_AUTONOMY_MODE (server-side), not tool args.
    Exploit requires confirmation in manual/semi and pentest.exploit.active.
    """
    return await run_start_phase(
        engine_id=engine_id,
        phase=phase,
        playbook_id=playbook_id,
        targets=targets,
        options=options,
        confirmation_token=confirmation_token,
    )


@mcp.tool()
async def engine_get_run(run_id: str) -> str:
    """Poll an engine run by run_id."""
    return await run_get_run(run_id=run_id)


@mcp.tool()
async def engine_cancel_run(run_id: str) -> str:
    """Best-effort cancel of an engine run."""
    return await run_cancel_run(run_id=run_id)


@mcp.tool()
async def engine_list_playbooks(engine_id: str | None = None) -> str:
    """List MVP playbook stubs (stable ids for PROJETOSIN-196)."""
    return await run_list_playbooks(engine_id=engine_id)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
