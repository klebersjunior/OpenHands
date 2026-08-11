"""Persist append-only custody chain (PROJETOSIN-199)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custody import CustodyEventRow
from shared.custody import GENESIS_PREV_HASH, build_custody_event
from shared.otel_setup import emit_custody_append
from shared.redaction import redact_mapping


class CustodyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _latest_hash(self, engagement_id: uuid.UUID) -> str:
        row = await self.db.scalar(
            select(CustodyEventRow)
            .where(CustodyEventRow.engagement_id == engagement_id)
            .order_by(CustodyEventRow.ts.desc(), CustodyEventRow.id.desc())
            .limit(1)
        )
        if row is None:
            return GENESIS_PREV_HASH
        return row.hash

    async def append(
        self,
        *,
        engagement_id: uuid.UUID,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: dict | None = None,
    ) -> CustodyEventRow:
        prev = await self._latest_hash(engagement_id)
        built = build_custody_event(
            engagement_id=str(engagement_id),
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            prev_hash=prev,
            metadata=metadata or {},
        )
        # Persist the same canonical ts string used in the hash (Zulu).
        ts_value = datetime.fromisoformat(built.ts.replace("Z", "+00:00"))
        row = CustodyEventRow(
            id=uuid.UUID(built.id),
            ts=ts_value,
            engagement_id=engagement_id,
            actor=built.actor,
            action=built.action,
            resource_type=built.resource_type,
            resource_id=built.resource_id,
            prev_hash=built.prev_hash,
            hash=built.hash,
            metadata_redacted=redact_mapping(built.metadata_redacted),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        emit_custody_append(
            engagement_id=str(engagement_id),
            custody_id=str(row.id),
            action=action,
        )
        return row

    async def list_for_engagement(
        self,
        engagement_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CustodyEventRow], int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 200)
        base = (
            select(CustodyEventRow)
            .where(CustodyEventRow.engagement_id == engagement_id)
            .order_by(CustodyEventRow.ts.asc(), CustodyEventRow.id.asc())
        )
        total = await self.db.scalar(
            select(func.count()).select_from(
                select(CustodyEventRow.id)
                .where(CustodyEventRow.engagement_id == engagement_id)
                .subquery()
            )
        )
        rows = (
            await self.db.scalars(
                base.offset((page - 1) * page_size).limit(page_size)
            )
        ).all()
        return list(rows), int(total or 0)
