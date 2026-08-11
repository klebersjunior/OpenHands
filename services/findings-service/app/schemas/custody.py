from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CustodyAppendRequest(BaseModel):
    engagement_id: uuid.UUID
    actor: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustodyEventOut(BaseModel):
    id: uuid.UUID
    ts: datetime
    engagement_id: uuid.UUID
    actor: str
    action: str
    resource_type: str
    resource_id: str
    prev_hash: str
    hash: str
    metadata_redacted: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class CustodyListResponse(BaseModel):
    items: list[CustodyEventOut]
    total: int
