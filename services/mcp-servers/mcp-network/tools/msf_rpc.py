"""net_msf_rpc_execute / net_msf_session_list — allowlisted Metasploit RPC."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from clients.msf_rpc_client import (
    MsfClientError,
    MsfConfigError,
    MsfModuleNotAllowedError,
    MsfRpcClient,
)
from shared.confirmation import ConfirmationRequiredError, require_confirmation
from shared.normalize import ScopeViolationError, assert_in_scope
from shared.tool_result import err, ok

ExecuteRunner = Callable[[str, dict[str, Any] | None], Awaitable[dict[str, Any]]]
SessionsRunner = Callable[[], Awaitable[list[dict[str, Any]]]]

EXECUTE_TOOL = "net_msf_rpc_execute"
EXECUTE_GATE = "net_msf_rpc_execute"
SESSIONS_TOOL = "net_msf_session_list"


def _rhost_from_options(options: dict[str, Any] | None) -> str | None:
    if not options:
        return None
    for key in ("RHOSTS", "RHOST", "rhosts", "rhost"):
        value = options.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            # RHOSTS may be space/CSV separated — validate first host only here;
            # full list validated below.
            return text
    return None


def _split_hosts(raw: str) -> list[str]:
    parts: list[str] = []
    for chunk in raw.replace(",", " ").split():
        item = chunk.strip()
        if item:
            parts.append(item)
    return parts


async def run_msf_rpc_execute(
    *,
    module: str,
    options: dict[str, Any] | None = None,
    engagement_id: str,
    confirmation_token: str | None = None,
    runner: ExecuteRunner | None = None,
) -> str:
    # Scope: require RHOST/RHOSTS in-scope before any RPC (fail-closed).
    rhosts_raw = _rhost_from_options(options)
    if not rhosts_raw:
        return err(
            "invalid_args",
            message="options.RHOSTS (or RHOST) is required for scoped execute",
        )
    try:
        for host in _split_hosts(rhosts_raw):
            assert_in_scope(host)
    except ScopeViolationError as exc:
        return err(exc.code, target=exc.target, message=str(exc))

    gate_payload = {
        "module": module,
        "engagement_id": engagement_id,
        "tool": EXECUTE_TOOL,
        "rhosts": rhosts_raw,
    }
    try:
        await require_confirmation(
            EXECUTE_GATE,
            gate_payload,
            confirmation_token=confirmation_token,
        )
    except ConfirmationRequiredError as exc:
        return err(**exc.as_dict())

    async def _default(mod: str, opts: dict[str, Any] | None) -> dict[str, Any]:
        return await MsfRpcClient().execute_module(mod, opts)

    run = runner or _default
    try:
        result = await run(module, options)
    except MsfModuleNotAllowedError as exc:
        return err(**exc.as_dict())
    except MsfConfigError as exc:
        return err(**exc.as_dict())
    except MsfClientError as exc:
        return err(**exc.as_dict())
    except Exception as exc:  # noqa: BLE001
        return err("msf_failed", message=str(exc)[:300])

    return ok({"tool": EXECUTE_TOOL, "engagement_id": engagement_id, **result})


async def run_msf_session_list(
    *,
    engagement_id: str,
    runner: SessionsRunner | None = None,
) -> str:
    async def _default() -> list[dict[str, Any]]:
        return await MsfRpcClient().list_sessions()

    run = runner or _default
    try:
        sessions = await run()
    except MsfConfigError as exc:
        return err(**exc.as_dict())
    except MsfClientError as exc:
        return err(**exc.as_dict())
    except Exception as exc:  # noqa: BLE001
        return err("msf_failed", message=str(exc)[:300])

    return ok(
        {
            "tool": SESSIONS_TOOL,
            "engagement_id": engagement_id,
            "sessions": sessions,
        }
    )
