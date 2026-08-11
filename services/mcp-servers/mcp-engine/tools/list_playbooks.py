"""engine_list_playbooks — MVP catalog (+ stubs for 196)."""

from __future__ import annotations

import json
from pathlib import Path

from shared.tool_result import err, ok

_CATALOG_PATH = Path(__file__).resolve().parents[1] / "playbooks" / "catalog.json"


def _load_catalog() -> list[dict]:
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return data


async def run_list_playbooks(*, engine_id: str | None = None) -> str:
    catalog = _load_catalog()
    if engine_id:
        engine_id = engine_id.strip().lower()
        if engine_id not in ("pentestagent", "cai"):
            return err("invalid_engine", engine_id=engine_id)
        catalog = [
            pb
            for pb in catalog
            if engine_id in (pb.get("engine_ids") or ["pentestagent", "cai"])
        ]
    playbooks = [
        {
            "id": pb["id"],
            "title": pb["title"],
            "phases": list(pb.get("phases") or []),
            "domains": list(pb.get("domains") or []),
        }
        for pb in catalog
    ]
    return ok({"playbooks": playbooks})
