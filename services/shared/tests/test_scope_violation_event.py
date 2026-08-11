"""AC-199-4 — scope_violation emits canonical span/event name."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SERVICES_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICES_ROOT))


def _load_mcp_normalize():
    """Load mcp-servers/shared/normalize without shadowing services.shared."""
    path = SERVICES_ROOT / "mcp-servers" / "shared" / "normalize.py"
    spec = importlib.util.spec_from_file_location("mcp_normalize_ac199", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mcp_normalize_ac199"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_ac_199_4_scope_violation_canonical_event(monkeypatch):
    from shared.otel_setup import EVENT_SCOPE_VIOLATION, attach_inmemory_exporter

    exporter = attach_inmemory_exporter()
    monkeypatch.setenv("PENTEST_SCOPE_ALLOWLIST", "example.com")
    monkeypatch.delenv("ENGAGEMENT_ID", raising=False)

    normalize = _load_mcp_normalize()

    with pytest.raises(normalize.ScopeViolationError):
        normalize.assert_in_scope("evil.out-of-scope.test")

    spans = exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert EVENT_SCOPE_VIOLATION in names
    hit = next(s for s in spans if s.name == EVENT_SCOPE_VIOLATION)
    assert hit.attributes.get("error_code") == "scope_violation"
    assert "evil.out-of-scope.test" in str(hit.attributes.get("target"))
