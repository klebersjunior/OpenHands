"""Shared helpers for mcp-network tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

USE_REAL_BINARIES_ENV = "MCP_NETWORK_USE_REAL_BINARIES"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def use_real_binaries() -> bool:
    """Default off — CI never needs real nmap/GVM/msfrpcd daemons."""
    return os.environ.get(USE_REAL_BINARIES_ENV, "0").strip() == "1"


def fixture_path(name: str) -> Path:
    return FIXTURES_DIR / name


def stub_finding(
    *,
    title: str,
    severity: str,
    asset: str,
    endpoint: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "severity": severity,
        "asset": asset,
        "endpoint": endpoint,
        "evidence": {"raw": extra or {}},
    }


def truncate_text(value: str, *, limit: int = 4000) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."
