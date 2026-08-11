"""net_gvm_start_scan — intrusive GVM/OpenVAS scan start (confirmation gate)."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from clients.gvm_client import GvmClient, GvmClientError, GvmConfigError
from shared.confirmation import ConfirmationRequiredError, require_confirmation
from shared.normalize import ScopeViolationError, assert_targets_in_scope
from shared.tool_result import err, ok

Runner = Callable[[list[str], str | None], Awaitable[dict[str, Any]]]
TOOL_NAME = "net_gvm_start_scan"
GATE_NAME = "net_gvm_start_scan"


async def run_gvm_start_scan(
    *,
    targets: list[str],
    engagement_id: str,
    config_id: str | None = None,
    confirmation_token: str | None = None,
    runner: Runner | None = None,
) -> str:
    if not targets:
        return err("invalid_args", message="targets must be a non-empty list")

    try:
        assert_targets_in_scope(targets)
    except ScopeViolationError as exc:
        return err(exc.code, target=exc.target, message=str(exc))

    gate_payload = {
        "targets": targets,
        "engagement_id": engagement_id,
        "config_id": config_id,
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

    async def _default(targets_: list[str], config_id_: str | None) -> dict[str, Any]:
        return await GvmClient().start_scan(targets_, config_id=config_id_)

    run = runner or _default
    try:
        result = await run(targets, config_id)
    except GvmConfigError as exc:
        return err(**exc.as_dict())
    except GvmClientError as exc:
        return err(**exc.as_dict())
    except Exception as exc:  # noqa: BLE001
        return err("gvm_failed", message=str(exc)[:300])

    return ok(
        {
            "tool": TOOL_NAME,
            "engagement_id": engagement_id,
            **result,
        }
    )
