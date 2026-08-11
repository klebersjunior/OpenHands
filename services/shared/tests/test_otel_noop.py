"""AC-199-1 — no OTLP endpoint → no-op exporter; setup succeeds."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVICES_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICES_ROOT))


def test_ac_199_1_otel_noop_without_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("PENTEST_OTEL_ENABLED", raising=False)

    from shared import otel_setup

    otel_setup._INITIALIZED = False
    otel_setup._PROVIDER = None

    assert otel_setup.otel_enabled() is False
    provider = otel_setup.setup_otel("test-noop-service", force=True)
    assert provider is not None

    # Spans can still be created (in-process) without export crash.
    otel_setup.emit_event("pentest.mcp.tool", attributes={"tool": "noop"})
    tracer = otel_setup.get_tracer()
    with tracer.start_as_current_span("manual") as span:
        span.set_attribute("ok", True)


def test_ac_199_1_explicit_disable_with_endpoint(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")
    monkeypatch.setenv("PENTEST_OTEL_ENABLED", "false")

    from shared import otel_setup

    assert otel_setup.otel_enabled() is False
