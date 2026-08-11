"""MCP tool span helper (PROJETOSIN-199).

Uses the OpenTelemetry API directly to avoid clashing with this package's
``shared`` namespace (mcp-servers/shared vs services/shared).
"""

from __future__ import annotations

import functools
import re
from contextlib import contextmanager
from typing import Any, Awaitable, Callable, Iterator, TypeVar

EVENT_MCP_TOOL = "pentest.mcp.tool"
_SENSITIVE_KEY_RE = re.compile(
    r"(authorization|api[_-]?key|session[_-]?api[_-]?key|password|token|cookie)",
    re.IGNORECASE,
)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def _safe_attrs(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        if _SENSITIVE_KEY_RE.search(str(key)):
            out[str(key)] = "[REDACTED]"
        elif isinstance(value, (bool, int, float, str)):
            out[str(key)] = value
        elif value is None:
            continue
        else:
            out[str(key)] = str(value)
    return out


@contextmanager
def mcp_tool_span(
    tool: str,
    *,
    engagement_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any]:
    from opentelemetry import trace

    tracer = trace.get_tracer("pentest.mcp")
    attrs = _safe_attrs({"tool": tool, **(attributes or {})})
    if engagement_id:
        attrs["engagement.id"] = engagement_id
    with tracer.start_as_current_span(EVENT_MCP_TOOL) as span:
        for key, value in attrs.items():
            span.set_attribute(str(key), value)
        try:
            yield span
            span.set_attribute("ok", True)
        except Exception as exc:
            span.set_attribute("ok", False)
            span.set_attribute("error_code", type(exc).__name__)
            raise


def with_mcp_tool_span(tool_name: str) -> Callable[[F], F]:
    """Decorator for async MCP tool entrypoints."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            engagement_id = kwargs.get("engagement_id")
            if engagement_id is not None:
                engagement_id = str(engagement_id)
            with mcp_tool_span(tool_name, engagement_id=engagement_id):
                return await fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
