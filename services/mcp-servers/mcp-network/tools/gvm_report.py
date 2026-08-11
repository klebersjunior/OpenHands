"""net_gvm_get_report — fetch GVM report and post OpenVAS findings."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from clients.gvm_client import (
    GvmClient,
    GvmClientError,
    GvmConfigError,
    findings_from_gvm_report,
)
from shared.findings_client import FindingsAuthError, FindingsClient
from shared.normalize import normalize_finding
from shared.tool_result import err, ok

Runner = Callable[[str], Awaitable[dict[str, Any]]]
TOOL_NAME = "net_gvm_get_report"


async def run_gvm_get_report(
    *,
    scan_id: str,
    engagement_id: str,
    findings: FindingsClient | None = None,
    runner: Runner | None = None,
) -> str:
    if not scan_id or not str(scan_id).strip():
        return err("invalid_args", message="scan_id is required")

    async def _default(scan_id_: str) -> dict[str, Any]:
        return await GvmClient().get_report(scan_id_)

    run = runner or _default
    try:
        result = await run(str(scan_id).strip())
    except GvmConfigError as exc:
        return err(**exc.as_dict())
    except GvmClientError as exc:
        return err(**exc.as_dict())
    except Exception as exc:  # noqa: BLE001
        return err("gvm_failed", message=str(exc)[:300])

    report = result.get("report") if isinstance(result, dict) else None
    if not isinstance(report, dict):
        report = {}

    payloads = findings_from_gvm_report(
        engagement_id=engagement_id,
        report=report,
        normalize_finding=normalize_finding,
    )
    client = findings or FindingsClient()
    posted: list[dict[str, Any]] = []
    try:
        for payload in payloads:
            posted.append(await client.post_finding(payload))
    except FindingsAuthError as exc:
        return err("findings_auth", status_code=exc.status_code)

    return ok(
        {
            "tool": TOOL_NAME,
            "scan_id": scan_id,
            "status": result.get("status") if isinstance(result, dict) else None,
            "findings_count": len(posted),
            "findings": posted,
        }
    )
