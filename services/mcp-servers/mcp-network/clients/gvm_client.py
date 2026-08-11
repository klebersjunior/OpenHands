"""OpenVAS/GVM client — stub by default; real GMP/HTTP when binaries flag + GVM_URL."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import httpx

from tools._common import fixture_path, use_real_binaries

GVM_URL_ENV = "GVM_URL"
GVM_USER_ENV = "GVM_USER"
GVM_PASSWORD_ENV = "GVM_PASSWORD"


class GvmConfigError(RuntimeError):
    code = "gvm_config"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message}


class GvmClientError(RuntimeError):
    code = "gvm_failed"

    def __init__(self, message: str, *, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.status_code is not None:
            payload["status_code"] = self.status_code
        return payload


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise GvmConfigError(f"{name} is unset (fail-closed)")
    return value


class GvmClient:
    """Minimal GVM adapter.

    Real mode expects an internal HTTP/GMP bridge at ``GVM_URL`` (credentials
    only from env). Stub mode returns fixture-shaped scan/report payloads so
    CI never needs a Greenbone stack.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 60.0,
    ):
        self._force_stub = not use_real_binaries()
        if self._force_stub:
            self.base_url = (base_url or "http://gvm-stub").rstrip("/")
            self.username = username or "stub"
            self.password = password or "stub"
        else:
            self.base_url = (base_url or _require_env(GVM_URL_ENV)).rstrip("/")
            self.username = username if username is not None else _require_env(GVM_USER_ENV)
            self.password = (
                password if password is not None else _require_env(GVM_PASSWORD_ENV)
            )
        self._transport = transport
        self._timeout = timeout
        # Never log password (AppSec).

    def _load_fixture(self) -> dict[str, Any]:
        path = fixture_path("gvm_report_sample.json")
        return json.loads(path.read_text(encoding="utf-8"))

    async def start_scan(
        self,
        targets: list[str],
        *,
        config_id: str | None = None,
    ) -> dict[str, Any]:
        if self._force_stub:
            scan_id = f"stub-scan-{uuid.uuid4()}"
            return {
                "scan_id": scan_id,
                "status": "queued",
                "targets": targets,
                "config_id": config_id or "stub-full-and-fast",
                "mode": "stub",
            }

        url = f"{self.base_url}/api/v1/scans"
        payload = {
            "targets": targets,
            "config_id": config_id,
        }
        # Basic auth — credentials from env only.
        auth = httpx.BasicAuth(self.username, self.password)
        async with httpx.AsyncClient(
            transport=self._transport, timeout=self._timeout
        ) as client:
            resp = await client.post(url, json=payload, auth=auth)
        if resp.status_code >= 400:
            raise GvmClientError(
                f"GVM start_scan failed ({resp.status_code})",
                status_code=resp.status_code,
            )
        data = resp.json()
        scan_id = data.get("scan_id") or data.get("id")
        if not scan_id:
            raise GvmClientError("GVM response missing scan_id")
        return {
            "scan_id": str(scan_id),
            "status": data.get("status", "queued"),
            "targets": targets,
            "config_id": config_id,
            "mode": "real",
        }

    async def get_report(self, scan_id: str) -> dict[str, Any]:
        if self._force_stub:
            fixture = self._load_fixture()
            return {
                "scan_id": scan_id,
                "status": "done",
                "mode": "stub",
                "report": fixture,
            }

        url = f"{self.base_url}/api/v1/scans/{scan_id}/report"
        auth = httpx.BasicAuth(self.username, self.password)
        async with httpx.AsyncClient(
            transport=self._transport, timeout=self._timeout
        ) as client:
            resp = await client.get(url, auth=auth)
        if resp.status_code >= 400:
            raise GvmClientError(
                f"GVM get_report failed ({resp.status_code})",
                status_code=resp.status_code,
            )
        data = resp.json()
        return {
            "scan_id": scan_id,
            "status": data.get("status", "done"),
            "mode": "real",
            "report": data.get("report") or data,
        }


def findings_from_gvm_report(
    *,
    engagement_id: str,
    report: dict[str, Any],
    normalize_finding,
) -> list[dict[str, Any]]:
    """Map GVM/OpenVAS report results to Findings payloads (source_tool=openvas)."""
    payloads: list[dict[str, Any]] = []
    results = report.get("results") or report.get("vulnerabilities") or []
    if not isinstance(results, list):
        results = []

    for item in results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("name") or item.get("title") or "OpenVAS finding")
        severity = str(item.get("severity") or "medium").lower()
        if severity not in ("critical", "high", "medium", "low", "info"):
            # OpenVAS often uses numeric CVSS — coarse map
            try:
                score = float(severity)
                if score >= 9:
                    severity = "critical"
                elif score >= 7:
                    severity = "high"
                elif score >= 4:
                    severity = "medium"
                elif score > 0:
                    severity = "low"
                else:
                    severity = "info"
            except ValueError:
                severity = "medium"
        asset = str(item.get("host") or item.get("asset") or "unknown")
        endpoint = item.get("port")
        if endpoint is not None:
            endpoint = str(endpoint)
        payloads.append(
            normalize_finding(
                engagement_id=engagement_id,
                source_tool="openvas",
                title=title[:256],
                description=str(item.get("description") or title),
                severity=severity,
                asset=asset,
                endpoint=endpoint,
                evidence={"raw": item},
                tags=["network", "openvas", "gvm"],
            )
        )

    if not payloads:
        payloads.append(
            normalize_finding(
                engagement_id=engagement_id,
                source_tool="openvas",
                title="OpenVAS scan completed (no results)",
                description="GVM report contained no vulnerability rows.",
                severity="info",
                asset=str(report.get("target") or "unknown"),
                endpoint=None,
                evidence={"raw": {"summary_keys": list(report.keys())[:20]}},
                tags=["network", "openvas", "gvm"],
            )
        )
    return payloads
