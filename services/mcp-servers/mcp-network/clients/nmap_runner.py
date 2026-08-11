"""Nmap runner — stub by default; real binary only when MCP_NETWORK_USE_REAL_BINARIES=1."""

from __future__ import annotations

import asyncio
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from tools._common import fixture_path, use_real_binaries

NMAP_BIN_ENV = "NMAP_BIN"

# Conceptual flag sets from PROJETOSIN-198 (not exploit payloads).
NMAP_PROFILE_ARGS: dict[str, list[str]] = {
    "discovery": ["-sn", "-T3", "--top-ports", "100"],
    "safe": [
        "-sV",
        "-T3",
        "--version-intensity",
        "2",
        "--top-ports",
        "1000",
    ],
    "full": ["-sV", "-sC", "-sU", "-T4", "-p-"],
}


class NmapRunnerError(RuntimeError):
    code = "nmap_failed"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message}


def nmap_binary() -> str:
    return (os.environ.get(NMAP_BIN_ENV) or shutil.which("nmap") or "nmap").strip()


def build_nmap_args(
    targets: list[str],
    profile: str,
    ports: str | None = None,
) -> list[str]:
    if profile not in NMAP_PROFILE_ARGS:
        raise NmapRunnerError(f"Unsupported nmap profile: {profile}")
    args = ["-oX", "-", *NMAP_PROFILE_ARGS[profile]]
    if ports and profile != "discovery":
        args.extend(["-p", ports])
    args.extend(targets)
    return args


def parse_nmap_xml(xml_text: str) -> list[dict[str, Any]]:
    """Normalize nmap XML hosts/ports into finding-shaped dicts."""
    findings: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise NmapRunnerError(f"Invalid nmap XML: {exc}") from exc

    for host in root.findall("host"):
        addr_el = host.find("address")
        asset = (
            addr_el.get("addr")
            if addr_el is not None and addr_el.get("addr")
            else "unknown"
        )
        hostname_el = host.find("hostnames/hostname")
        if hostname_el is not None and hostname_el.get("name"):
            asset = hostname_el.get("name") or asset

        status = host.find("status")
        if status is not None and status.get("state") == "up":
            findings.append(
                {
                    "title": f"Host up: {asset}",
                    "severity": "info",
                    "asset": asset,
                    "endpoint": None,
                    "evidence": {"raw": {"host": asset, "state": "up"}},
                }
            )

        for port in host.findall("ports/port"):
            state_el = port.find("state")
            if state_el is None or state_el.get("state") != "open":
                continue
            portid = port.get("portid") or "?"
            proto = port.get("protocol") or "tcp"
            service_el = port.find("service")
            service = (
                service_el.get("name")
                if service_el is not None and service_el.get("name")
                else "unknown"
            )
            product = (
                service_el.get("product")
                if service_el is not None
                else None
            )
            title = f"Open port {portid}/{proto} ({service})"
            if product:
                title = f"{title} — {product}"
            findings.append(
                {
                    "title": title,
                    "severity": "info",
                    "asset": asset,
                    "endpoint": f"{portid}/{proto}",
                    "evidence": {
                        "raw": {
                            "port": portid,
                            "protocol": proto,
                            "service": service,
                            "product": product,
                        }
                    },
                }
            )
    return findings


def load_stub_xml() -> str:
    path = fixture_path("nmap_sample.xml")
    return path.read_text(encoding="utf-8")


async def run_nmap(
    targets: list[str],
    profile: str,
    ports: str | None = None,
) -> list[dict[str, Any]]:
    args = build_nmap_args(targets, profile, ports)
    if not use_real_binaries():
        return parse_nmap_xml(load_stub_xml())

    binary = nmap_binary()
    if not shutil.which(binary) and not Path(binary).is_file():
        raise NmapRunnerError(f"nmap binary not found: {binary}")

    proc = await asyncio.create_subprocess_exec(
        binary,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    if proc.returncode not in (0, 1):
        # nmap may return non-zero on partial failures; still try parse
        err = stderr.decode("utf-8", errors="replace")[:400]
        if not stdout:
            raise NmapRunnerError(err or "nmap failed")
    xml_text = stdout.decode("utf-8", errors="replace")
    if not xml_text.strip():
        raise NmapRunnerError(
            stderr.decode("utf-8", errors="replace")[:400] or "empty nmap output"
        )
    return parse_nmap_xml(xml_text)
