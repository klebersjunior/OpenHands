"""Custody chain API (PROJETOSIN-199)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.middleware.auth import AuthContext, require_authenticated, require_capability
from app.schemas.custody import (
    CustodyAppendRequest,
    CustodyEventOut,
    CustodyListResponse,
)
from app.services.custody_service import CustodyService

internal_router = APIRouter(prefix="/internal", tags=["custody-internal"])
router = APIRouter(prefix="/api/pentest/engagements", tags=["custody"])


@internal_router.post("/custody", response_model=CustodyEventOut, status_code=201)
async def append_custody(
    payload: CustodyAppendRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = require_authenticated(),
):
    """Internal append — session-key auth; metadata is redacted before persist."""
    row = await CustodyService(db).append(
        engagement_id=payload.engagement_id,
        actor=payload.actor or ctx.user_id,
        action=payload.action,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        metadata=payload.metadata,
    )
    return CustodyEventOut.model_validate(row)


@router.get("/{engagement_id}/custody", response_model=CustodyListResponse)
async def list_custody(
    engagement_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = require_capability("pentest.findings.view"),
):
    items, total = await CustodyService(db).list_for_engagement(
        engagement_id, page=page, page_size=page_size
    )
    return CustodyListResponse(
        items=[CustodyEventOut.model_validate(i) for i in items],
        total=total,
    )
