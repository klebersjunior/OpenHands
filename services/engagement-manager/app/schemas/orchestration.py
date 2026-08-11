from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal[
    "pending",
    "running",
    "awaiting_confirmation",
    "succeeded",
    "failed",
    "cancelled",
]
StepStatus = Literal[
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "awaiting_confirmation",
    "skipped",
    "blocked_missing_server",
    "blocked_capability",
]


class PlaybookPhaseOut(BaseModel):
    id: str
    tools: list[str] = Field(default_factory=list)
    engine_phase: str
    gate: str = "none"


class PlaybookOut(BaseModel):
    id: str
    title: str
    domain: str
    engine_id: str
    phases: list[PlaybookPhaseOut]


class PlaybookListResponse(BaseModel):
    playbooks: list[PlaybookOut]


class CreateRunRequest(BaseModel):
    playbook_id: str
    domain: str | None = None
    engine_id: str | None = None
    start_phase: str | None = None
    # Optional: when omitted/empty, EngMgr hydrates from engagement scope
    # allow-rule target_values (fail-closed if none). Always revalidated.
    targets: list[str] | None = None
    # Ignored if present — autonomy is server-side only (engagement + env).
    autonomy_mode: str | None = None


class CreateRunResponse(BaseModel):
    run_id: uuid.UUID
    status: RunStatus


class OrchestrationStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: int
    phase_id: str
    engine_phase: str
    gate: str
    status: str
    engine_run_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    finding_ids: list[Any] = Field(default_factory=list)


class OrchestrationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_id: uuid.UUID
    playbook_id: str
    domain: str
    engine_id: str
    status: str
    current_phase: str | None
    targets: list[str] = Field(default_factory=list)
    finding_ids: list[Any] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    steps: list[OrchestrationStepOut] = Field(default_factory=list)


class OrchestrationRunListResponse(BaseModel):
    items: list[OrchestrationRunOut]
    total: int
