"""Local playbook catalog + merge with engine_list_playbooks stub (197)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Strict playbook id — blocks path traversal (AppSec).
PLAYBOOK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,126}$")

_PLAYBOOKS_DIR = Path(__file__).resolve().parents[2] / "playbooks"

DOMAIN_TOOL_ALLOWLIST: dict[str, frozenset[str]] = {
    "web": frozenset(
        {
            "engine_start_phase",
            "engine_get_run",
            "engine_cancel_run",
            "engine_list_playbooks",
            "engine_list_engines",
        }
    ),
    "network": frozenset(
        {
            "engine_start_phase",
            "engine_get_run",
            "engine_cancel_run",
            "engine_list_playbooks",
            "engine_list_engines",
            "net_nmap_scan",
            "net_gvm_scan",
            "net_msf_session",
        }
    ),
    "mobile": frozenset(
        {
            "engine_start_phase",
            "engine_get_run",
            "engine_cancel_run",
            "engine_list_playbooks",
            "engine_list_engines",
            "mobsf_static",
            "mobsf_dynamic",
            "adb_install",
        }
    ),
}


@dataclass(frozen=True)
class PlaybookPhase:
    id: str
    tools: tuple[str, ...]
    engine_phase: str
    gate: str = "none"


@dataclass(frozen=True)
class Playbook:
    id: str
    title: str
    domain: str
    engine_id: str
    phases: tuple[PlaybookPhase, ...]


def _parse_playbook(data: dict[str, Any]) -> Playbook:
    phases: list[PlaybookPhase] = []
    for raw in data.get("phases") or []:
        phases.append(
            PlaybookPhase(
                id=str(raw["id"]),
                tools=tuple(str(t) for t in (raw.get("tools") or [])),
                engine_phase=str(raw.get("engine_phase") or raw["id"]),
                gate=str(raw.get("gate") or "none"),
            )
        )
    return Playbook(
        id=str(data["id"]),
        title=str(data.get("title") or data["id"]),
        domain=str(data.get("domain") or "web"),
        engine_id=str(data.get("engine_id") or "pentestagent"),
        phases=tuple(phases),
    )


def load_local_playbooks() -> dict[str, Playbook]:
    catalog: dict[str, Playbook] = {}
    if not _PLAYBOOKS_DIR.is_dir():
        return catalog
    for path in sorted(_PLAYBOOKS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "id" not in data:
            continue
        pb_id = str(data["id"])
        if not PLAYBOOK_ID_RE.match(pb_id):
            continue
        # Filename must match id — blocks smuggling via odd paths.
        if path.stem != pb_id:
            continue
        catalog[pb_id] = _parse_playbook(data)
    return catalog


def get_playbook(playbook_id: str) -> Playbook | None:
    if not PLAYBOOK_ID_RE.match(playbook_id):
        return None
    return load_local_playbooks().get(playbook_id)


def list_playbooks(
    *,
    engine_playbooks: list[dict[str, Any]] | None = None,
) -> list[Playbook]:
    """Merge local MVP catalog with optional engine_list_playbooks results."""
    local = load_local_playbooks()
    merged: dict[str, Playbook] = dict(local)
    for raw in engine_playbooks or []:
        if not isinstance(raw, dict) or "id" not in raw:
            continue
        pb_id = str(raw["id"])
        if not PLAYBOOK_ID_RE.match(pb_id) or pb_id in merged:
            continue
        # Engine-only entries may omit full phase detail — keep minimal shape.
        phases_raw = raw.get("phases") or []
        phases: list[PlaybookPhase] = []
        if phases_raw and isinstance(phases_raw[0], dict):
            for p in phases_raw:
                phases.append(
                    PlaybookPhase(
                        id=str(p.get("id") or p.get("engine_phase") or "recon"),
                        tools=tuple(str(t) for t in (p.get("tools") or ["engine_start_phase"])),
                        engine_phase=str(p.get("engine_phase") or p.get("id") or "recon"),
                        gate=str(p.get("gate") or "none"),
                    )
                )
        else:
            for name in phases_raw:
                phases.append(
                    PlaybookPhase(
                        id=str(name),
                        tools=("engine_start_phase",),
                        engine_phase=str(name),
                    )
                )
        merged[pb_id] = Playbook(
            id=pb_id,
            title=str(raw.get("title") or pb_id),
            domain=str((raw.get("domains") or ["web"])[0]),
            engine_id=str(raw.get("engine_id") or "pentestagent"),
            phases=tuple(phases),
        )
    return sorted(merged.values(), key=lambda p: p.id)
