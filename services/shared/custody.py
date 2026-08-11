"""Chain-of-custody hash helpers (PROJETOSIN-199)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .redaction import redact_mapping

GENESIS_PREV_HASH = "0" * 64


@dataclass
class CustodyEvent:
    """Append-only custody link (hash computed separately)."""

    engagement_id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    prev_hash: str
    metadata_redacted: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    hash: str = ""


def canonical_json(payload: dict[str, Any]) -> str:
    """Stable JSON for hashing — sorted keys, no whitespace variance."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _canonical_ts(ts: Any) -> str:
    """Normalize timestamps so SQLite naive round-trips match hash input."""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            body = ts.strftime("%Y-%m-%dT%H:%M:%S.%f")
        else:
            body = ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")
        return body + "Z"
    text = str(ts).strip()
    if text.endswith("+00:00"):
        text = text[:-6]
    elif text.endswith("Z"):
        text = text[:-1]
    return text + "Z"


def event_payload_for_hash(event: CustodyEvent | dict[str, Any]) -> dict[str, Any]:
    data = asdict(event) if isinstance(event, CustodyEvent) else dict(event)
    data.pop("hash", None)
    return {
        "id": str(data.get("id", "")),
        "ts": _canonical_ts(data.get("ts", "")),
        "engagement_id": str(data.get("engagement_id", "")),
        "actor": str(data.get("actor", "")),
        "action": str(data.get("action", "")),
        "resource_type": str(data.get("resource_type", "")),
        "resource_id": str(data.get("resource_id", "")),
        "prev_hash": str(data.get("prev_hash", "")),
        "metadata_redacted": redact_mapping(data.get("metadata_redacted") or {}),
    }


def compute_custody_hash(
    prev_hash: str, event: CustodyEvent | dict[str, Any]
) -> str:
    """
    hash = SHA-256(prev_hash || canonical_json(event_without_hash))
    """
    body = canonical_json(event_payload_for_hash(event))
    material = f"{prev_hash or GENESIS_PREV_HASH}{body}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def build_custody_event(
    *,
    engagement_id: str,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    prev_hash: str | None,
    metadata: dict[str, Any] | None = None,
    event_id: str | None = None,
    ts: str | None = None,
) -> CustodyEvent:
    event = CustodyEvent(
        id=event_id or str(uuid.uuid4()),
        ts=_canonical_ts(ts or datetime.now(timezone.utc)),
        engagement_id=str(engagement_id),
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        prev_hash=prev_hash or GENESIS_PREV_HASH,
        metadata_redacted=redact_mapping(metadata or {}),
    )
    event.hash = compute_custody_hash(event.prev_hash, event)
    return event


def _as_event_dict(raw: CustodyEvent | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, CustodyEvent):
        return asdict(raw)
    return {
        "id": str(raw.get("id", "")),
        "ts": str(raw.get("ts", "")),
        "engagement_id": str(raw.get("engagement_id", "")),
        "actor": str(raw.get("actor", "")),
        "action": str(raw.get("action", "")),
        "resource_type": str(raw.get("resource_type", "")),
        "resource_id": str(raw.get("resource_id", "")),
        "prev_hash": str(raw.get("prev_hash", "")),
        "hash": str(raw.get("hash", "")),
        "metadata_redacted": raw.get("metadata_redacted") or {},
    }


def verify_chain(events: list[CustodyEvent | dict[str, Any]]) -> bool:
    """Return True iff every link's hash matches recomputation and prev linkage."""
    expected_prev = GENESIS_PREV_HASH
    for raw in events:
        data = _as_event_dict(raw)
        if data["prev_hash"] != expected_prev:
            return False
        recomputed = compute_custody_hash(data["prev_hash"], data)
        if recomputed != data["hash"]:
            return False
        expected_prev = data["hash"]
    return True
