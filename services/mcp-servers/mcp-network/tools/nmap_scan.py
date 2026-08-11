"""net_nmap_scan — scoped nmap with profile-based confirmation gate."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from clients.nmap_runner import NmapRunnerError, run_nmap
from shared.confirmation import ConfirmationRequiredError, require_confirmation
from shared.findings_client import FindingsAuthError, FindingsClient
from shared.normalize import (
    ScopeViolationError,
    Severity,
    assert_targets_in_scope,
    normalize_finding,
)
from shared.tool_result import err, ok

NmapProfile = Literal["discovery", "safe", "full"]
Runner = Callable[[list[str], str, str | None], Awaitable[list[dict[str, Any]]]]

TOOL_NAME = "net_nmap_scan"
# Gate name registered in ACTIVE_TOOLS — only invoked for profile=full.
GATE_NAME = "net_nmap_scan"
_SEVERITIES = frozenset({"critical", "high", "medium", "low", "info"})


def _as_severity(raw: Any) -> Severity:
    value = str(raw or "info").lower()
    if value in _SEVERITIES:
        return value  # type: ignore[return-value]
    return "info"


async def run_nmap_scan(
    *,
    targets: list[str],
    engagement_id: str,
    profile: NmapProfile = "safe",
    ports: str | None = None,
    confirmation_token: str | None = None,
    findings: FindingsClient | None = None,
    runner: Runner | None = None,
) -> str:
    if not targets:
        return err("invalid_args", message="targets must be a non-empty list")
    if profile not in ("discovery", "safe", "full"):
        return err("invalid_args", message=f"unsupported profile: {profile}")

    try:
        assert_targets_in_scope(targets)
    except ScopeViolationError as exc:
        return err(exc.code, target=exc.target, message=str(exc))

    if profile == "full":
        gate_payload = {
            "targets": targets,
            "engagement_id": engagement_id,
            "profile": profile,
            "tool": TOOL_NAME,
        }
        try:
            await require_confirmation(
                GATE_NAME,
                gate_payload,
                confirmation_token=confirmation_token,
            )
        except ConfirmationRequiredError as exc:
            return err(**exc.as_dict())

    run = runner or run_nmap
    try:
        items = await run(targets, profile, ports)
    except NmapRunnerError as exc:
        return err(**exc.as_dict())
    except Exception as exc:  # noqa: BLE001
        return err("nmap_failed", message=str(exc)[:300])

    client = findings or FindingsClient()
    posted: list[dict[str, Any]] = []
    try:
        for item in items:
            payload = normalize_finding(
                engagement_id=engagement_id,
                source_tool="nmap",
                title=str(item.get("title") or "nmap finding"),
                severity=_as_severity(item.get("severity")),
                asset=item.get("asset"),
                endpoint=item.get("endpoint"),
                evidence=item.get("evidence"),
                description=f"nmap profile={profile}",
                tags=["network", "nmap", profile],
            )
            posted.append(await client.post_finding(payload))
    except FindingsAuthError as exc:
        return err("findings_auth", status_code=exc.status_code)

    return ok(
        {
            "tool": TOOL_NAME,
            "profile": profile,
            "targets": targets,
            "findings_count": len(posted),
            "findings": posted,
        }
    )
