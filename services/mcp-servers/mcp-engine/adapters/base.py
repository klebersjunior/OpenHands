"""Engine adapter protocol and in-memory run registry (PROJETOSIN-197)."""

from __future__ import annotations

import ipaddress
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol
from urllib.parse import urlparse

RunStatus = Literal[
    "queued",
    "running",
    "awaiting_confirmation",
    "succeeded",
    "failed",
    "cancelled",
]

CanonicalPhase = Literal["recon", "scan", "analyze", "exploit"]

PHASE_ALIASES: dict[str, CanonicalPhase] = {
    "recon": "recon",
    "scan": "scan",
    "analyze": "analyze",
    "exploit": "exploit",
    "enumeration": "scan",
    "exploitation": "exploit",
}

ENGAGEMENT_ID_ENV = "ENGAGEMENT_ID"
CAPABILITIES_ENV = "PENTEST_CAPABILITIES"
ENGINE_URL_ALLOWLIST_ENV = "PENTEST_ENGINE_URL_ALLOWLIST"
CAP_SCAN_PASSIVE = "pentest.scan.passive"
CAP_EXPLOIT_ACTIVE = "pentest.exploit.active"

# Cloud / link-local metadata hostnames blocked even if mis-allowlisted.
_BLOCKED_ENGINE_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.",
        "ip6-localhost",
        "ip6-loopback",
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
    }
)

_OLLAMA_ENV_KEYS = (
    "OLLAMA_HOST",
    "OLLAMA_BASE_URL",
)
_LLM_BASE_ENV_KEYS = (
    "PENTEST_ENGINE_LLM_BASE_URL",
    "LITELLM_BASE_URL",
    "OPENAI_API_BASE",
)
_OLLAMA_DEFAULT_PORT = 11434


@dataclass
class RunRecord:
    run_id: str
    engine_id: str
    phase: CanonicalPhase
    status: RunStatus
    engagement_id: str
    targets: list[str] = field(default_factory=list)
    playbook_id: str | None = None
    summary: str | None = None
    finding_ids: list[str] = field(default_factory=list)
    error: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


class EngineAdapter(Protocol):
    engine_id: str
    capabilities: list[str]

    def status(self) -> str:
        """ready | unavailable | disabled."""
        ...

    async def start(
        self,
        *,
        run: RunRecord,
        registry: "RunRegistry",
    ) -> RunRecord:
        ...

    async def get(self, run: RunRecord) -> RunRecord:
        ...

    async def cancel(self, run: RunRecord) -> RunRecord:
        ...


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(
        self,
        *,
        engine_id: str,
        phase: CanonicalPhase,
        engagement_id: str,
        targets: list[str] | None = None,
        playbook_id: str | None = None,
        options: dict[str, Any] | None = None,
        status: RunStatus = "queued",
    ) -> RunRecord:
        run = RunRecord(
            run_id=str(uuid.uuid4()),
            engine_id=engine_id,
            phase=phase,
            status=status,
            engagement_id=engagement_id,
            targets=list(targets or []),
            playbook_id=playbook_id,
            options=dict(options or {}),
        )
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def put(self, run: RunRecord) -> RunRecord:
        self._runs[run.run_id] = run
        return run


_REGISTRY = RunRegistry()


def get_run_registry() -> RunRegistry:
    return _REGISTRY


def reset_run_registry() -> None:
    """Test helper — clear in-memory runs."""
    global _REGISTRY
    _REGISTRY = RunRegistry()


def normalize_phase(phase: str) -> CanonicalPhase | None:
    key = (phase or "").strip().lower()
    return PHASE_ALIASES.get(key)


def engagement_id_from_env() -> str:
    return os.environ.get(ENGAGEMENT_ID_ENV, "").strip()


def configured_capabilities() -> set[str] | None:
    """
    Optional launcher-injected capabilities (CSV).

    ``None`` means the launcher did not pass context — attach gating is
    documented as the caller's responsibility; tools do not invent RBAC.
    """
    raw = os.environ.get(CAPABILITIES_ENV)
    if raw is None:
        return None
    return {part.strip() for part in raw.split(",") if part.strip()}


def emit_run_event(run: RunRecord) -> None:
    """Structured JSON log for PROJETOSIN-199 (no secrets / prompts)."""
    payload = {
        "event": "engine.run",
        "engagement_id": run.engagement_id,
        "run_id": run.run_id,
        "engine_id": run.engine_id,
        "phase": run.phase,
        "status": run.status,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload, default=str), file=sys.stdout, flush=True)


def engine_url_allowlist() -> set[str]:
    """Positive hostname allowlist for engine control-plane URLs (CSV)."""
    raw = os.environ.get(ENGINE_URL_ALLOWLIST_ENV, "")
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _expand_ipv4_literal(host: str) -> ipaddress.IPv4Address | None:
    """Parse dotted / abbreviated / decimal IPv4 (e.g. 127.1, 2130706433)."""
    if host.isdigit():
        try:
            value = int(host)
            if 0 <= value <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(value)
        except ValueError:
            return None
    parts = host.split(".")
    if not parts or not all(p.isdigit() for p in parts) or len(parts) > 4:
        try:
            return ipaddress.IPv4Address(host)
        except ValueError:
            return None
    nums = [int(p) for p in parts]
    if any(n < 0 or n > 255 for n in nums):
        # Allow single-octet forms above 255 only via full decimal path above.
        if len(nums) != 1 or nums[0] > 0xFFFFFFFF:
            return None
    if len(nums) == 1:
        n = nums[0]
        nums = [(n >> 24) & 255, (n >> 16) & 255, (n >> 8) & 255, n & 255]
    elif len(nums) == 2:
        nums = [nums[0], 0, 0, nums[1]]
    elif len(nums) == 3:
        nums = [nums[0], nums[1], 0, nums[2]]
    try:
        return ipaddress.IPv4Address(".".join(str(n) for n in nums))
    except ValueError:
        return None


def _host_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    ipv4 = _expand_ipv4_literal(host)
    if ipv4 is not None:
        return ipv4
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _is_blocked_engine_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_loopback or ip.is_link_local or ip.is_unspecified:
        return True
    if ip.is_multicast:
        return True
    # Link-local / metadata ranges (explicit — covers 169.254.0.0/16, fe80::/10).
    if isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network(
        "169.254.0.0/16"
    ):
        return True
    if isinstance(ip, ipaddress.IPv6Address) and ip in ipaddress.ip_network("fe80::/10"):
        return True
    return False


def assert_allowed_engine_url(url: str) -> str | None:
    """
    Fail-closed SSRF guard for engine control-plane URLs.

    Requires ``http`` scheme, no userinfo, and hostname present on
    ``PENTEST_ENGINE_URL_ALLOWLIST`` (compose service DNS / documented
    engagement hosts). Loopback, link-local, metadata, and abbreviated
    loopback encodings are always rejected.
    """
    raw = (url or "").strip()
    if not raw:
        return "engine URL missing"

    parsed = urlparse(raw)
    if parsed.scheme != "http":
        return "engine URL scheme must be http"
    if parsed.username is not None or parsed.password is not None:
        return "engine URL must not include userinfo"

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return "engine URL missing host"
    if host in _BLOCKED_ENGINE_HOSTNAMES or "metadata" in host:
        return f"engine URL host blocked: {host}"

    ip = _host_ip(host)
    if ip is not None and _is_blocked_engine_ip(ip):
        return f"engine URL host blocked: {host}"

    allow = engine_url_allowlist()
    if not allow:
        return f"{ENGINE_URL_ALLOWLIST_ENV} empty (fail-closed)"

    # IP literals must appear explicitly on the allowlist (no broad private CIDR).
    if ip is not None:
        candidates = {str(ip).lower(), host}
        if not candidates.intersection(allow):
            return f"engine URL host not in {ENGINE_URL_ALLOWLIST_ENV}"
        return None

    if host not in allow:
        return f"engine URL host not in {ENGINE_URL_ALLOWLIST_ENV}"
    return None


def _is_self_hosted_llm_endpoint(value: str) -> bool:
    """True when value points at Ollama / local self-hosted LLM."""
    lowered = value.strip().lower()
    if not lowered:
        return False
    if "ollama" in lowered:
        return True

    # Bare host:port without scheme (common for OLLAMA_HOST).
    candidate = lowered if "://" in lowered else f"http://{lowered}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return False

    port = parsed.port
    if port is None and ":11434" in lowered:
        port = _OLLAMA_DEFAULT_PORT

    ip = _host_ip(host)
    is_loopback_host = host in ("localhost", "localhost.") or (
        ip is not None and ip.is_loopback
    )
    # Canonical Ollama listen address: loopback + port 11434.
    return bool(is_loopback_host and port == _OLLAMA_DEFAULT_PORT)


def assert_no_ollama_llm() -> str | None:
    """Refuse engine LLM config that points at Ollama / self-hosted local."""
    for key in _OLLAMA_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return f"{key} must not be set (Ollama/self-hosted LLM forbidden)"

    for key in _LLM_BASE_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        if _is_self_hosted_llm_endpoint(value):
            return f"{key} must not point at Ollama/self-hosted LLM"
    return None
