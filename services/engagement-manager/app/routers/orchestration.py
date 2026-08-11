"""Orchestration API under EngMgr (PROJETOSIN-196).

Mounted at ``/api/pentest/engagements/{id}/orchestration/*`` so ingress
(``/api/pentest/engagements`` → EngMgr) routes correctly. Spec shorthand
``/api/engagements/.../orchestration`` maps to this prefix in this service.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.middleware.auth import AuthContext, require_capability
from app.schemas.orchestration import (
    CreateRunRequest,
    CreateRunResponse,
    OrchestrationRunListResponse,
    OrchestrationRunOut,
    PlaybookListResponse,
    PlaybookOut,
    PlaybookPhaseOut,
)
from app.services.orchestrator import OrchestratorService

router = APIRouter(
    prefix="/api/pentest/engagements/{engagement_id}/orchestration",
    tags=["orchestration"],
)


@router.get("/playbooks", response_model=PlaybookListResponse)
async def list_playbooks(
    engagement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = require_capability("pentest.engagement.view"),
):
    del engagement_id  # catalog is global; auth still requires engagement.view
    playbooks = await OrchestratorService(db).list_catalog()
    return PlaybookListResponse(
        playbooks=[
            PlaybookOut(
                id=p.id,
                title=p.title,
                domain=p.domain,
                engine_id=p.engine_id,
                phases=[
                    PlaybookPhaseOut(
                        id=ph.id,
                        tools=list(ph.tools),
                        engine_phase=ph.engine_phase,
                        gate=ph.gate,
                    )
                    for ph in p.phases
                ],
            )
            for p in playbooks
        ]
    )


@router.get("/runs", response_model=OrchestrationRunListResponse)
async def list_runs(
    engagement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = require_capability("pentest.engagement.view"),
):
    items, total = await OrchestratorService(db).list_runs(
        engagement_id, user_id=ctx.user_id
    )
    return OrchestrationRunListResponse(
        items=[OrchestrationRunOut.model_validate(i) for i in items],
        total=total,
    )


@router.post("/runs", response_model=CreateRunResponse, status_code=201)
async def create_run(
    engagement_id: uuid.UUID,
    payload: CreateRunRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = require_capability("pentest.scan.passive"),
):
    run = await OrchestratorService(db).create_run(
        engagement_id,
        payload,
        user_id=ctx.user_id,
        capabilities=ctx.capabilities,
    )
    return CreateRunResponse(run_id=run.id, status=run.status)  # type: ignore[arg-type]


@router.get("/runs/{run_id}", response_model=OrchestrationRunOut)
async def get_run(
    engagement_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = require_capability("pentest.engagement.view"),
):
    run = await OrchestratorService(db).get_run(
        engagement_id, run_id, user_id=ctx.user_id
    )
    return OrchestrationRunOut.model_validate(run)


@router.post("/runs/{run_id}/advance", response_model=OrchestrationRunOut)
async def advance_run(
    engagement_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = require_capability("pentest.scan.passive"),
):
    """Advance past confirmation gate (reuses confirmation channel pattern)."""
    # Exploit phase still checked inside runner for pentest.exploit.active.
    run = await OrchestratorService(db).advance(
        engagement_id,
        run_id,
        user_id=ctx.user_id,
        capabilities=ctx.capabilities,
    )
    return OrchestrationRunOut.model_validate(run)


@router.post("/runs/{run_id}/cancel", response_model=OrchestrationRunOut)
async def cancel_run(
    engagement_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = require_capability("pentest.scan.passive"),
):
    run = await OrchestratorService(db).cancel(
        engagement_id, run_id, user_id=ctx.user_id
    )
    return OrchestrationRunOut.model_validate(run)
