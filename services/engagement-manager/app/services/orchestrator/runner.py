"""Playbook state machine runner (PROJETOSIN-196)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.engagement import Engagement, ScopeRule
from app.models.orchestration import OrchestrationRun, OrchestrationStep
from app.schemas.orchestration import CreateRunRequest
from app.services.orchestrator.catalog import (
    DOMAIN_TOOL_ALLOWLIST,
    Playbook,
    get_playbook,
    list_playbooks,
)
from app.services.orchestrator.custody import emit_engine_run_event
from app.services.orchestrator.engine_client import EngineClient, get_engine_client
from app.services.scope_validator import is_target_allowed
from shared.capabilities import PentestCapability

TERMINAL_RUN = frozenset({"succeeded", "failed", "cancelled"})
CONFIRMATION_AUTONOMY = frozenset({"manual", "semi_autonomous"})


class OrchestratorService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        engine: EngineClient | None = None,
    ):
        self.db = db
        self.engine = engine or get_engine_client()

    async def list_catalog(self) -> list[Playbook]:
        engine_pbs = self.engine.list_playbooks().get("playbooks") or []
        return list_playbooks(engine_playbooks=engine_pbs)

    async def _get_engagement(
        self, engagement_id: uuid.UUID, *, user_id: str
    ) -> Engagement:
        eng = await self.db.get(Engagement, engagement_id)
        if eng is None or eng.created_by != user_id:
            raise HTTPException(status_code=404, detail="Engagement not found")
        return eng

    async def _scope_rules(
        self, engagement_id: uuid.UUID
    ) -> list[tuple[str, str, str]]:
        rows = (
            await self.db.scalars(
                select(ScopeRule).where(ScopeRule.engagement_id == engagement_id)
            )
        ).all()
        return [(r.rule_type, r.target_type, r.target_value) for r in rows]

    def _infer_target_type(self, target: str) -> str:
        if target.startswith("http://") or target.startswith("https://"):
            return "url"
        if "/" in target and any(c.isdigit() for c in target.split("/")[0]):
            return "cidr"
        parts = target.split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            return "ip"
        return "domain"

    def _validate_targets(
        self,
        rules: list[tuple[str, str, str]],
        targets: list[str],
    ) -> str | None:
        """Return scope_violation message if any target fails allowlist."""
        if not targets:
            return None
        if not rules:
            return "No scope rules configured (fail-closed)"
        for target in targets:
            ttype = self._infer_target_type(target)
            if not is_target_allowed(rules, target_type=ttype, target_value=target):
                return f"Target out of scope: {target}"
        return None

    def _phase_needs_confirmation(self, gate: str, autonomy_mode: str) -> bool:
        if gate != "confirmation":
            return False
        return autonomy_mode in CONFIRMATION_AUTONOMY

    def _has_capability(
        self, capabilities: list[PentestCapability] | list[str], needed: str
    ) -> bool:
        return needed in capabilities

    def _phase_requires_exploit_cap(self, engine_phase: str) -> bool:
        return engine_phase == "exploit"

    def _domain_tools_missing(self, playbook: Playbook, tools: tuple[str, ...]) -> bool:
        if any(t.startswith("net_") for t in tools):
            return not self.engine.domain_server_available("network")
        if playbook.domain == "mobile" and any(
            t.startswith("mobsf_") or t.startswith("adb_") for t in tools
        ):
            return not self.engine.domain_server_available("mobile")
        return False

    async def create_run(
        self,
        engagement_id: uuid.UUID,
        payload: CreateRunRequest,
        *,
        user_id: str,
        capabilities: list[PentestCapability] | list[str],
    ) -> OrchestrationRun:
        # Body autonomy_mode is ignored (no bypass).
        eng = await self._get_engagement(engagement_id, user_id=user_id)
        playbook = get_playbook(payload.playbook_id)
        if playbook is None:
            raise HTTPException(status_code=400, detail="Unknown or invalid playbook_id")

        domain = payload.domain or playbook.domain
        engine_id = payload.engine_id or playbook.engine_id
        if domain != playbook.domain:
            raise HTTPException(
                status_code=400, detail="domain does not match playbook"
            )

        allow = DOMAIN_TOOL_ALLOWLIST.get(domain, frozenset())
        for phase in playbook.phases:
            for tool in phase.tools:
                if tool not in allow and not tool.startswith("engine_"):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Tool {tool} not allowlisted for domain {domain}",
                    )

        start_idx = 0
        if payload.start_phase:
            ids = [p.id for p in playbook.phases]
            if payload.start_phase not in ids:
                raise HTTPException(status_code=400, detail="Invalid start_phase")
            start_idx = ids.index(payload.start_phase)

        targets = list(payload.targets or [])
        rules = await self._scope_rules(engagement_id)

        run = OrchestrationRun(
            engagement_id=engagement_id,
            playbook_id=playbook.id,
            domain=domain,
            engine_id=engine_id,
            status="pending",
            current_phase=None,
            finding_ids=[],
            created_by=user_id,
        )
        self.db.add(run)
        await self.db.flush()

        for i, phase in enumerate(playbook.phases):
            step = OrchestrationStep(
                run_id=run.id,
                sequence=i,
                phase_id=phase.id,
                engine_phase=phase.engine_phase,
                gate=phase.gate,
                status="pending",
                finding_ids=[],
            )
            self.db.add(step)
        await self.db.commit()
        run = await self.get_run(engagement_id, run.id, user_id=user_id)

        await self._execute_from(
            eng,
            run,
            playbook,
            start_idx=start_idx,
            targets=targets,
            rules=rules,
            capabilities=capabilities,
            confirmed=False,
        )
        return await self.get_run(engagement_id, run.id, user_id=user_id)

    async def _execute_from(
        self,
        eng: Engagement,
        run: OrchestrationRun,
        playbook: Playbook,
        *,
        start_idx: int,
        targets: list[str],
        rules: list[tuple[str, str, str]],
        capabilities: list[PentestCapability] | list[str],
        confirmed: bool,
    ) -> None:
        if run.status in TERMINAL_RUN:
            return

        steps = sorted(run.steps, key=lambda s: s.sequence)
        run.status = "running"
        run.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        for step in steps:
            if step.sequence < start_idx:
                if step.status == "pending":
                    step.status = "skipped"
                continue
            if step.status in (
                "succeeded",
                "skipped",
                "blocked_capability",
                "blocked_missing_server",
            ):
                continue
            if step.status == "cancelled":
                return

            # Capability gate for exploit (AC-196-7)
            if self._phase_requires_exploit_cap(step.engine_phase):
                if not self._has_capability(capabilities, "pentest.exploit.active"):
                    step.status = "blocked_capability"
                    step.error_code = "capability_denied"
                    step.error_message = "Missing pentest.exploit.active"
                    run.current_phase = step.phase_id
                    run.status = "succeeded"
                    run.updated_at = datetime.now(timezone.utc)
                    await self.db.commit()
                    emit_engine_run_event(
                        engagement_id=str(eng.id),
                        run_id=str(run.id),
                        engine_id=run.engine_id,
                        phase=step.engine_phase,
                        status="blocked_capability",
                    )
                    return

            # Confirmation gate (AC-196-2)
            if self._phase_needs_confirmation(step.gate, eng.autonomy_mode):
                if not confirmed:
                    step.status = "awaiting_confirmation"
                    run.status = "awaiting_confirmation"
                    run.current_phase = step.phase_id
                    run.updated_at = datetime.now(timezone.utc)
                    await self.db.commit()
                    emit_engine_run_event(
                        engagement_id=str(eng.id),
                        run_id=str(run.id),
                        engine_id=run.engine_id,
                        phase=step.engine_phase,
                        status="awaiting_confirmation",
                    )
                    return
                # advance() supplies confirmed=True once.

            # Domain server availability (198 network)
            phase_def = next(
                (p for p in playbook.phases if p.id == step.phase_id), None
            )
            tools = phase_def.tools if phase_def else ()
            if self._domain_tools_missing(playbook, tools):
                step.status = "blocked_missing_server"
                step.error_code = "blocked_missing_server"
                step.error_message = f"Domain MCP server unavailable for {playbook.domain}"
                run.status = "failed"
                run.error_code = "blocked_missing_server"
                run.error_message = step.error_message
                run.current_phase = step.phase_id
                run.updated_at = datetime.now(timezone.utc)
                await self.db.commit()
                return

            # Scope allowlist (AC-196-3) — fail closed before engine call
            scope_err = self._validate_targets(rules, targets)
            if scope_err is None and targets:
                # Also let stub reject forced violations
                pass
            if scope_err:
                step.status = "failed"
                step.error_code = "scope_violation"
                step.error_message = scope_err
                run.status = "failed"
                run.error_code = "scope_violation"
                run.error_message = scope_err
                run.current_phase = step.phase_id
                run.updated_at = datetime.now(timezone.utc)
                await self.db.commit()
                return

            step.status = "running"
            run.current_phase = step.phase_id
            run.status = "running"
            await self.db.commit()

            result = self.engine.start_phase(
                engine_id=run.engine_id,
                phase=step.engine_phase,
                playbook_id=run.playbook_id,
                targets=targets or None,
            )
            if not result.ok or result.run is None:
                code = result.error_code or "engine_error"
                step.status = "failed"
                step.error_code = code
                step.error_message = result.error_message
                run.status = "failed"
                run.error_code = code
                run.error_message = result.error_message
                run.updated_at = datetime.now(timezone.utc)
                await self.db.commit()
                emit_engine_run_event(
                    engagement_id=str(eng.id),
                    run_id=str(run.id),
                    engine_id=run.engine_id,
                    phase=step.engine_phase,
                    status="failed",
                    extra={"error_code": code},
                )
                return

            step.engine_run_id = result.run.run_id
            step.finding_ids = list(result.run.finding_ids)
            step.status = "succeeded"
            merged = list(run.finding_ids or [])
            for fid in result.run.finding_ids:
                if fid not in merged:
                    merged.append(fid)
            run.finding_ids = merged
            run.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            emit_engine_run_event(
                engagement_id=str(eng.id),
                run_id=str(run.id),
                engine_id=run.engine_id,
                phase=step.engine_phase,
                status="succeeded",
            )
            # Confirmation only applies once per advance cycle
            confirmed = False

        run.status = "succeeded"
        run.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def get_run(
        self,
        engagement_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        user_id: str,
    ) -> OrchestrationRun:
        await self._get_engagement(engagement_id, user_id=user_id)
        stmt = (
            select(OrchestrationRun)
            .where(
                OrchestrationRun.id == run_id,
                OrchestrationRun.engagement_id == engagement_id,
            )
            .options(selectinload(OrchestrationRun.steps))
        )
        run = await self.db.scalar(stmt)
        if run is None:
            raise HTTPException(status_code=404, detail="Orchestration run not found")
        return run

    async def list_runs(
        self, engagement_id: uuid.UUID, *, user_id: str
    ) -> tuple[list[OrchestrationRun], int]:
        await self._get_engagement(engagement_id, user_id=user_id)
        stmt = (
            select(OrchestrationRun)
            .where(OrchestrationRun.engagement_id == engagement_id)
            .options(selectinload(OrchestrationRun.steps))
            .order_by(OrchestrationRun.created_at.desc())
        )
        rows = list((await self.db.scalars(stmt)).all())
        return rows, len(rows)

    async def advance(
        self,
        engagement_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        user_id: str,
        capabilities: list[PentestCapability] | list[str],
        targets: list[str] | None = None,
    ) -> OrchestrationRun:
        eng = await self._get_engagement(engagement_id, user_id=user_id)
        run = await self.get_run(engagement_id, run_id, user_id=user_id)
        if run.status != "awaiting_confirmation":
            raise HTTPException(
                status_code=400,
                detail="Run is not awaiting confirmation",
            )
        playbook = get_playbook(run.playbook_id)
        if playbook is None:
            raise HTTPException(status_code=400, detail="Playbook no longer available")

        waiting = next(
            (s for s in run.steps if s.status == "awaiting_confirmation"), None
        )
        if waiting is None:
            raise HTTPException(status_code=400, detail="No step awaiting confirmation")

        waiting.status = "pending"
        rules = await self._scope_rules(engagement_id)
        await self._execute_from(
            eng,
            run,
            playbook,
            start_idx=waiting.sequence,
            targets=list(targets or []),
            rules=rules,
            capabilities=capabilities,
            confirmed=True,
        )
        return await self.get_run(engagement_id, run_id, user_id=user_id)

    async def cancel(
        self,
        engagement_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        user_id: str,
    ) -> OrchestrationRun:
        run = await self.get_run(engagement_id, run_id, user_id=user_id)
        if run.status in TERMINAL_RUN:
            raise HTTPException(status_code=400, detail="Run already terminal")

        for step in run.steps:
            if step.engine_run_id:
                self.engine.cancel_run(step.engine_run_id)
            if step.status in (
                "running",
                "pending",
                "awaiting_confirmation",
            ):
                step.status = "cancelled"
        run.status = "cancelled"
        run.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        emit_engine_run_event(
            engagement_id=str(engagement_id),
            run_id=str(run.id),
            engine_id=run.engine_id,
            phase=run.current_phase or "",
            status="cancelled",
        )
        return await self.get_run(engagement_id, run_id, user_id=user_id)
