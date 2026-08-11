"""OpenTelemetry bootstrap for pentest services (PROJETOSIN-199).

Exporter is a no-op when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is empty / unset
(or ``PENTEST_OTEL_ENABLED=false``). Never ships secrets — callers must
pass attributes through ``redact_mapping`` / helpers below.
"""

from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from .redaction import redact_mapping

# Canonical event / span names
EVENT_MCP_TOOL = "pentest.mcp.tool"
EVENT_RUNTIME_COMMAND = "pentest.runtime.command"
EVENT_FINDING_MUTATE = "pentest.finding.mutate"
EVENT_SCOPE_VIOLATION = "pentest.scope.violation"
EVENT_CONFIRMATION_GATE = "pentest.confirmation.gate"
EVENT_ENGINE_RUN = "pentest.engine.run"
EVENT_CUSTODY_APPEND = "pentest.custody.append"

_INITIALIZED = False
_PROVIDER: TracerProvider | None = None


def _env_truthy(name: str, default: str = "") -> bool:
    raw = os.environ.get(name, default).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def otlp_endpoint() -> str:
    return os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()


def otel_enabled() -> bool:
    """Enabled when explicitly true, or when endpoint is set and not disabled."""
    explicit = os.environ.get("PENTEST_OTEL_ENABLED")
    if explicit is not None and explicit.strip() != "":
        return _env_truthy("PENTEST_OTEL_ENABLED")
    return bool(otlp_endpoint())


def llm_bodies_enabled() -> bool:
    return _env_truthy("PENTEST_OTEL_LLM_BODIES", "false")


def deployment_mode() -> str:
    mode = os.environ.get("PENTEST_DEPLOYMENT_MODE", "").strip()
    if mode in {"electron", "server", "dev"}:
        return mode
    if os.environ.get("ELECTRON_RUN_AS_NODE") or os.environ.get(
        "PENTEST_ELECTRON_HOOKS_ENABLED", ""
    ).strip().lower() in {"1", "true", "yes", "on"}:
        return "electron"
    return os.environ.get("DEPLOYMENT_MODE", "dev").strip() or "dev"


def build_resource(service_name: str) -> Resource:
    attrs: dict[str, Any] = {
        "service.name": os.environ.get("OTEL_SERVICE_NAME", service_name).strip()
        or service_name,
        "deployment.mode": deployment_mode(),
    }
    engagement_id = os.environ.get("ENGAGEMENT_ID", "").strip()
    if engagement_id:
        attrs["engagement.id"] = engagement_id
    return Resource.create(attrs)


def setup_otel(
    service_name: str,
    *,
    force: bool = False,
    span_processor: Any | None = None,
) -> TracerProvider:
    """
    Initialize global TracerProvider.

    Without an OTLP endpoint (and without an injected processor), spans are
    recorded in-process but not exported — safe for CI.
    """
    global _INITIALIZED, _PROVIDER
    if _INITIALIZED and not force and span_processor is None:
        assert _PROVIDER is not None
        return _PROVIDER

    resource = build_resource(service_name)
    provider = TracerProvider(resource=resource)

    if span_processor is not None:
        provider.add_span_processor(span_processor)
    elif otel_enabled() and otlp_endpoint():
        # Lazy import so CI without exporter extras still imports this module
        # when endpoint is unset (no-op path).
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        headers_raw = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "").strip()
        headers: dict[str, str] = {}
        if headers_raw:
            for part in headers_raw.split(","):
                if "=" in part:
                    k, _, v = part.partition("=")
                    headers[k.strip()] = v.strip()
        exporter = OTLPSpanExporter(
            endpoint=_normalize_otlp_traces_url(otlp_endpoint()),
            headers=headers or None,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

    if force:
        # OTEL allows set_tracer_provider only once; tests need override.
        from opentelemetry.util._once import Once

        trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]
        trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]

    trace.set_tracer_provider(provider)
    _PROVIDER = provider
    _INITIALIZED = True
    return provider


def _normalize_otlp_traces_url(endpoint: str) -> str:
    """Accept collector base or full traces URL."""
    base = endpoint.rstrip("/")
    if base.endswith("/v1/traces"):
        return base
    return f"{base}/v1/traces"


def get_tracer(name: str = "pentest") -> Tracer:
    return trace.get_tracer(name)


def start_span(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "pentest",
) -> Span:
    tracer = get_tracer(tracer_name)
    span = tracer.start_span(name)
    for key, value in redact_mapping(attributes or {}).items():
        if value is None:
            continue
        span.set_attribute(str(key), _otel_attr(value))
    return span


def emit_event(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
    ok: bool = True,
    error_code: str | None = None,
    tracer_name: str = "pentest",
) -> None:
    """Emit a short-lived span representing a canonical pentest event."""
    attrs = dict(attributes or {})
    attrs["ok"] = ok
    if error_code:
        attrs["error_code"] = error_code
    span = start_span(name, attributes=attrs, tracer_name=tracer_name)
    if not ok:
        span.set_status(Status(StatusCode.ERROR, error_code or "error"))
    span.end()


def emit_scope_violation(
    *,
    target: str,
    engagement_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    attrs: dict[str, Any] = {
        "target": target,
        "error_code": "scope_violation",
    }
    if engagement_id:
        attrs["engagement.id"] = engagement_id
    if extra:
        attrs.update(extra)
    emit_event(EVENT_SCOPE_VIOLATION, attributes=attrs, ok=False, error_code="scope_violation")


def emit_finding_mutate(
    *,
    action: str,
    finding_id: str,
    engagement_id: str,
    extra: dict[str, Any] | None = None,
) -> None:
    attrs: dict[str, Any] = {
        "action": action,
        "finding.id": finding_id,
        "engagement.id": engagement_id,
    }
    if extra:
        attrs.update(extra)
    emit_event(EVENT_FINDING_MUTATE, attributes=attrs, ok=True)


def emit_custody_append(
    *,
    engagement_id: str,
    custody_id: str,
    action: str,
    extra: dict[str, Any] | None = None,
) -> None:
    attrs: dict[str, Any] = {
        "engagement.id": engagement_id,
        "custody.id": custody_id,
        "action": action,
    }
    if extra:
        attrs.update(extra)
    emit_event(EVENT_CUSTODY_APPEND, attributes=attrs, ok=True)


def attach_inmemory_exporter() -> Any:
    """Test helper: force a provider with InMemorySpanExporter."""
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    setup_otel(
        "test-service",
        force=True,
        span_processor=SimpleSpanProcessor(exporter),
    )
    return exporter


def _otel_attr(value: Any) -> Any:
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_otel_attr(v) for v in value]
    return str(value)
