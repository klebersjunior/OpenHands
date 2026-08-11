"""engine_start_phase — start a canonical engine phase with scope/autonomy gates."""

from __future__ import annotations

from typing import Any

from adapters import get_adapters
from adapters.base import (
    CAP_EXPLOIT_ACTIVE,
    CAP_SCAN_PASSIVE,
    assert_no_ollama_llm,
    configured_capabilities,
    engagement_id_from_env,
    get_run_registry,
    normalize_phase,
)
from adapters.cai import cai_enabled
from shared.confirmation import ConfirmationRequiredError, require_confirmation
from shared.findings_client import FindingsClient
from shared.normalize import ScopeViolationError, assert_in_scope
from shared.tool_result import err, ok

EXPLOIT_GATE_TOOL = "engine_exploit"


async def run_start_phase(
    *,
    engine_id: str,
    phase: str,
    playbook_id: str | None = None,
    targets: list[str] | None = None,
    options: dict[str, Any] | None = None,
    confirmation_token: str | None = None,
    findings: FindingsClient | None = None,
) -> str:
    # Autonomy / engine selection must never come from free-form agent override.
    if options and "autonomy_mode" in options:
        return err(
            "invalid_options",
            message="autonomy_mode is server-side only (PENTEST_AUTONOMY_MODE)",
        )

    engine_key = (engine_id or "").strip().lower()
    if engine_key == "cai" and not cai_enabled():
        return err("engine_not_enabled", engine_id=engine_key)

    adapters = get_adapters()
    adapter = adapters.get(engine_key)
    if adapter is None:
        return err("invalid_engine", engine_id=engine_id)

    canonical = normalize_phase(phase)
    if canonical is None:
        return err("invalid_phase", phase=phase)

    ollama_err = assert_no_ollama_llm()
    if ollama_err:
        return err("engine_unavailable", message=ollama_err)

    caps = configured_capabilities()
    if caps is not None:
        if CAP_SCAN_PASSIVE not in caps and CAP_EXPLOIT_ACTIVE not in caps:
            return err(
                "capability_denied",
                message="profile lacks pentest.scan.passive",
                required=CAP_SCAN_PASSIVE,
            )
        if canonical == "exploit" and CAP_EXPLOIT_ACTIVE not in caps:
            return err(
                "capability_denied",
                message="exploit phase requires pentest.exploit.active",
                required=CAP_EXPLOIT_ACTIVE,
            )

    target_list = list(targets or [])
    for target in target_list:
        try:
            assert_in_scope(target)
        except ScopeViolationError as exc:
            return err(exc.code, target=exc.target, message=str(exc))

    if canonical == "exploit":
        gate_payload = {
            "engine_id": engine_key,
            "phase": canonical,
            "targets": target_list,
            "playbook_id": playbook_id,
            "tool": "engine_start_phase",
        }
        try:
            await require_confirmation(
                EXPLOIT_GATE_TOOL,
                gate_payload,
                confirmation_token=confirmation_token,
            )
        except ConfirmationRequiredError as exc:
            return err(**exc.as_dict())

    if adapter.status() != "ready":
        return err("engine_unavailable", engine_id=engine_key, status=adapter.status())

    engagement_id = engagement_id_from_env()
    if not engagement_id:
        engagement_id = (options or {}).get("engagement_id") or "unknown"

    registry = get_run_registry()
    run = registry.create(
        engine_id=engine_key,
        phase=canonical,
        engagement_id=str(engagement_id),
        targets=target_list,
        playbook_id=playbook_id,
        options=options,
        status="queued",
    )

    # Inject findings client into adapter when provided (tests).
    if findings is not None and hasattr(adapter, "_findings"):
        adapter._findings = findings  # type: ignore[attr-defined]
        if hasattr(adapter, "_transport") and findings._transport is not None:
            adapter._transport = findings._transport  # type: ignore[attr-defined]

    run = await adapter.start(run=run, registry=registry)
    if run.error == "engine_unavailable":
        return err("engine_unavailable", run_id=run.run_id, engine_id=engine_key)
    if run.error == "engine_not_enabled":
        return err("engine_not_enabled", run_id=run.run_id, engine_id=engine_key)

    return ok({"run_id": run.run_id, "status": run.status})
