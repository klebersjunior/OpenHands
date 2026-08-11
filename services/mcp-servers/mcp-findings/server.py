"""mcp-findings — stdio MCP for Findings Service (PROJETOSIN-205)."""

from __future__ import annotations

import json
import os
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

from shared.findings_client import FindingsClient, FindingsAuthError, FindingsClientError

mcp = FastMCP("mcp-findings")


def _dump(payload: Any) -> str:
    return json.dumps(payload, default=str)


@mcp.tool()
async def findings_get_scope() -> str:
    """Return the engagement allowlist and autonomy from server env."""
    allowlist = os.environ.get("PENTEST_SCOPE_ALLOWLIST", "").strip()
    assets = [item.strip() for item in allowlist.split(",") if item.strip()]
    return _dump(
        {
            "ok": True,
            "engagement_id": os.environ.get("PENTEST_ENGAGEMENT_ID") or None,
            "autonomy_mode": os.environ.get(
                "PENTEST_AUTONOMY_MODE", "semi_autonomous"
            ),
            "allowlist": assets,
            "scope_confirmed": len(assets) > 0,
        }
    )


@mcp.tool()
async def findings_list(engagement_id: str, page: int = 1) -> str:
    """List findings already filed for this engagement (Achados)."""
    client = FindingsClient()
    try:
        result = await client.list_findings(
            engagement_id=engagement_id, page=page
        )
        return _dump({"ok": True, **result})
    except (FindingsAuthError, FindingsClientError) as exc:
        return _dump({"ok": False, "error": str(exc)})


@mcp.tool()
async def findings_create(
    engagement_id: str,
    title: str,
    severity: str,
    source_tool: str,
    description: str = "",
    asset: str = "",
    endpoint: str = "",
) -> str:
    """Create a finding in Findings Service. It appears under Achados."""
    payload: dict[str, Any] = {
        "engagement_id": engagement_id,
        "title": title,
        "severity": severity,
        "source_tool": source_tool,
    }
    if description:
        payload["description"] = description
    if asset:
        payload["asset"] = asset
    if endpoint:
        payload["endpoint"] = endpoint
    client = FindingsClient()
    try:
        result = await client.post_finding(payload)
        return _dump({"ok": True, **result})
    except (FindingsAuthError, FindingsClientError) as exc:
        return _dump({"ok": False, "error": str(exc)})


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
