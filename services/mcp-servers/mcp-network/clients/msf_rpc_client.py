"""Metasploit RPC client — allowlisted module orchestration only (no free console).

Never embeds exploit payloads/PoCs. Real RPC is used only when
``MCP_NETWORK_USE_REAL_BINARIES=1`` and ``MSF_RPC_*`` env is set.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from tools._common import truncate_text, use_real_binaries

MSF_RPC_HOST_ENV = "MSF_RPC_HOST"
MSF_RPC_PORT_ENV = "MSF_RPC_PORT"
MSF_RPC_TOKEN_ENV = "MSF_RPC_TOKEN"
DEFAULT_MSF_RPC_PORT = "55553"

# Prefix allowlist (PROJETOSIN-198). Expand only via deliberate review/ADR.
MSF_ALLOWED_PREFIXES: tuple[str, ...] = (
    "auxiliary/",
    "scanner/",
)

# Documented exploit/ subset — module path prefixes only (orchestration allowlist).
# Do not add payload bodies or PoC code to this repository.
MSF_ALLOWED_EXPLOIT_PREFIXES: tuple[str, ...] = (
    "exploit/multi/handler",
    "exploit/windows/smb/",
    "exploit/linux/samba/",
)

_REDACT_KEYS = frozenset(
    {
        "password",
        "passwd",
        "pass",
        "secret",
        "token",
        "api_key",
        "apikey",
        "hash",
        "ntlm",
        "credential",
        "credentials",
        "cookie",
        "authorization",
        "private_key",
        "ssh_key",
    }
)

_FORBIDDEN_OPTION_KEYS = frozenset(
    {
        "setg",
        "console",
        "execute",
        "run_command",
        "cmd",
        "command",
        "shell",
    }
)


class MsfModuleNotAllowedError(RuntimeError):
    code = "module_not_allowed"

    def __init__(self, module: str):
        self.module = module
        super().__init__(f"Metasploit module not allowlisted: {module}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "module": self.module,
            "message": str(self),
        }


class MsfConfigError(RuntimeError):
    code = "msf_config"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message}


class MsfClientError(RuntimeError):
    code = "msf_failed"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message}


def normalize_module_name(module: str) -> str:
    value = module.strip().lstrip("/")
    # Reject path traversal / console escapes
    if ".." in value or "\n" in value or "\r" in value or ";" in value:
        raise MsfModuleNotAllowedError(module)
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", value):
        raise MsfModuleNotAllowedError(module)
    return value


def assert_module_allowed(module: str) -> str:
    normalized = normalize_module_name(module)
    for prefix in MSF_ALLOWED_PREFIXES:
        if normalized.startswith(prefix):
            return normalized
    for prefix in MSF_ALLOWED_EXPLOIT_PREFIXES:
        if normalized == prefix.rstrip("/") or normalized.startswith(prefix):
            return normalized
    raise MsfModuleNotAllowedError(normalized)


def assert_options_safe(options: dict[str, Any] | None) -> dict[str, Any]:
    """Reject free-console / setg / arbitrary shell option keys."""
    cleaned: dict[str, Any] = {}
    for key, value in (options or {}).items():
        key_l = str(key).strip().lower()
        if key_l in _FORBIDDEN_OPTION_KEYS:
            raise MsfClientError(f"Option key not allowed: {key}")
        if key_l.startswith("setg"):
            raise MsfClientError(f"Option key not allowed: {key}")
        cleaned[str(key)] = value
    return cleaned


def redact_value(key: str, value: Any) -> Any:
    if key.lower() in _REDACT_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(key, item) for item in value]
    if isinstance(value, str) and len(value) > 200:
        return truncate_text(value, limit=200)
    return value


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    return {str(k): redact_value(str(k), v) for k, v in data.items()}


class MsfRpcClient:
    """HTTP bridge to internal msfrpcd.

    MVP talks to an internal HTTP adapter at ``http://{host}:{port}/rpc`` when
    real binaries are enabled. Stub mode returns deterministic fixtures without
    contacting any daemon.
    """

    def __init__(
        self,
        *,
        host: str | None = None,
        port: str | int | None = None,
        token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 60.0,
    ):
        self._force_stub = not use_real_binaries()
        self.host = (
            host
            or os.environ.get(MSF_RPC_HOST_ENV, "msfrpcd").strip()
            or "msfrpcd"
        )
        self.port = str(
            port
            if port is not None
            else (os.environ.get(MSF_RPC_PORT_ENV) or DEFAULT_MSF_RPC_PORT)
        ).strip()
        self.token = (
            token
            if token is not None
            else os.environ.get(MSF_RPC_TOKEN_ENV, "").strip()
        )
        self._transport = transport
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _headers(self) -> dict[str, str]:
        if not self.token and not self._force_stub:
            raise MsfConfigError(f"{MSF_RPC_TOKEN_ENV} is unset (fail-closed)")
        headers = {"Content-Type": "application/json"}
        if self.token:
            # Token from env only — never logged.
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def execute_module(
        self,
        module: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        allowed = assert_module_allowed(module)
        safe_opts = assert_options_safe(options)

        if self._force_stub:
            return {
                "module": allowed,
                "job_id": "stub-job-1",
                "status": "completed",
                "mode": "stub",
                "output": truncate_text(
                    f"stub execute {allowed} options={sorted(safe_opts.keys())}"
                ),
            }

        url = f"{self.base_url}/rpc/module/execute"
        payload = {"module": allowed, "options": safe_opts}
        async with httpx.AsyncClient(
            transport=self._transport, timeout=self._timeout
        ) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
        if resp.status_code >= 400:
            raise MsfClientError(f"MSF RPC execute failed ({resp.status_code})")
        data = resp.json() if resp.content else {}
        if not isinstance(data, dict):
            data = {"raw": data}
        output = data.get("output") or data.get("result") or ""
        if isinstance(output, str):
            data["output"] = truncate_text(output)
        return redact_mapping({**data, "module": allowed, "mode": "real"})

    async def list_sessions(self) -> list[dict[str, Any]]:
        if self._force_stub:
            return [
                redact_mapping(
                    {
                        "id": 1,
                        "type": "meterpreter",
                        "info": "stub session",
                        "tunnel_local": "127.0.0.1:4444",
                        "tunnel_peer": "10.0.0.5:49152",
                        "username": "stub",
                        "password": "should-not-leak",
                    }
                )
            ]

        url = f"{self.base_url}/rpc/sessions"
        async with httpx.AsyncClient(
            transport=self._transport, timeout=self._timeout
        ) as client:
            resp = await client.get(url, headers=self._headers())
        if resp.status_code >= 400:
            raise MsfClientError(f"MSF RPC sessions failed ({resp.status_code})")
        data = resp.json() if resp.content else []
        if isinstance(data, dict):
            sessions = data.get("sessions") or data.get("items") or []
        else:
            sessions = data
        if not isinstance(sessions, list):
            sessions = []
        return [
            redact_mapping(item) if isinstance(item, dict) else {"value": str(item)}
            for item in sessions
        ]
