"""mcp-network — stdio MCP server for network runtime (PROJETOSIN-198)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from mcp.server.fastmcp import FastMCP

from tools.gvm_report import run_gvm_get_report
from tools.gvm_scan import run_gvm_start_scan
from tools.msf_rpc import run_msf_rpc_execute, run_msf_session_list
from tools.nmap_scan import run_nmap_scan

mcp = FastMCP("mcp-network")

NmapProfile = Literal["discovery", "safe", "full"]


@mcp.tool()
async def net_nmap_scan(
    targets: list[str],
    engagement_id: str,
    profile: NmapProfile = "safe",
    ports: str | None = None,
    confirmation_token: str | None = None,
) -> str:
    """Run nmap against in-scope targets.

    Profiles discovery/safe require pentest.scan.passive.
    Profile full requires pentest.scan.active + confirmation in semi mode.
    Autonomy comes from PENTEST_AUTONOMY_MODE (server-side), not tool args.
    """
    return await run_nmap_scan(
        targets=targets,
        engagement_id=engagement_id,
        profile=profile,
        ports=ports,
        confirmation_token=confirmation_token,
    )


@mcp.tool()
async def net_gvm_start_scan(
    targets: list[str],
    engagement_id: str,
    config_id: str | None = None,
    confirmation_token: str | None = None,
) -> str:
    """Start an OpenVAS/GVM scan (pentest.scan.active + confirmation in semi).

    Autonomy comes from PENTEST_AUTONOMY_MODE (server-side), not tool args.
    """
    return await run_gvm_start_scan(
        targets=targets,
        engagement_id=engagement_id,
        config_id=config_id,
        confirmation_token=confirmation_token,
    )


@mcp.tool()
async def net_gvm_get_report(scan_id: str, engagement_id: str) -> str:
    """Fetch a GVM/OpenVAS report and post findings (pentest.scan.active)."""
    return await run_gvm_get_report(scan_id=scan_id, engagement_id=engagement_id)


@mcp.tool()
async def net_msf_rpc_execute(
    module: str,
    options: dict[str, Any],
    engagement_id: str,
    confirmation_token: str | None = None,
) -> str:
    """Execute an allowlisted Metasploit module via internal RPC.

    Requires pentest.exploit.active + confirmation in semi mode.
    Modules outside the allowlist return module_not_allowed.
    Autonomy comes from PENTEST_AUTONOMY_MODE (server-side), not tool args.
    """
    return await run_msf_rpc_execute(
        module=module,
        options=options,
        engagement_id=engagement_id,
        confirmation_token=confirmation_token,
    )


@mcp.tool()
async def net_msf_session_list(engagement_id: str) -> str:
    """List Metasploit sessions (credentials redacted). Requires pentest.exploit.active."""
    return await run_msf_session_list(engagement_id=engagement_id)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
