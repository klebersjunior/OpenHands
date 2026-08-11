from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_FALLBACK_ANDROID_EMULATOR = "budtmo/docker-android:emulator_13.0"
_FALLBACK_MOBSF = "opensecurity/mobile-security-framework-mobsf:latest"
_FALLBACK_RUNTIME_NETWORK = "ghcr.io/heimdall/runtime-network:latest"
_FALLBACK_GVM = "greenbone/gvmd:stable"
_FALLBACK_MSF_RPC_PORT = 55553
_FALLBACK_GVM_MIN_RAM_GB = 8
_FALLBACK_FINDINGS_URL = "http://findings-service:8000"


def _repo_root() -> Path:
    # Host checkout: app/config.py → engagement-manager → services → repo root.
    # Docker image: /app/app/config.py — parents[3] does not exist (IndexError).
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config" / "defaults.json").is_file():
            return parent
    return here.parent


def _defaults_json() -> dict:
    path = _repo_root() / "config" / "defaults.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _defaults_images() -> dict[str, str]:
    images = _defaults_json().get("images") or {}
    return {k: v for k, v in images.items() if isinstance(v, str)}


def _defaults_ports() -> dict[str, int]:
    ports = _defaults_json().get("ports") or {}
    return {k: int(v) for k, v in ports.items() if isinstance(v, int)}


def _defaults_pentest_network() -> dict:
    pentest = _defaults_json().get("pentest") or {}
    network = pentest.get("network") or {}
    return network if isinstance(network, dict) else {}


_IMAGES = _defaults_images()
_PORTS = _defaults_ports()
_NETWORK = _defaults_pentest_network()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    engmgr_db_url: str = "sqlite+aiosqlite:///:memory:"
    # No insecure default — set SESSION_API_KEY (or PENTEST_ALLOW_DEV_SESSION_KEY=1
    # only when intentionally using the scaffold key in local/dev).
    session_api_key: str = ""
    default_pentest_profile: str = "pentester"
    compose_work_dir: str = "/tmp/engmgr-compose"
    # When true, provisioner skips real docker compose (tests / scaffold)
    provisioner_dry_run: bool = True
    # Image pins — defaults.json is source of truth; env overrides for ops.
    android_emulator_image: str = _IMAGES.get(
        "androidEmulator", _FALLBACK_ANDROID_EMULATOR
    )
    mobsf_image: str = _IMAGES.get("mobsf", _FALLBACK_MOBSF)
    runtime_network_image: str = _IMAGES.get(
        "runtimeNetwork", _FALLBACK_RUNTIME_NETWORK
    )
    gvm_image: str = _IMAGES.get("gvm", _FALLBACK_GVM)
    msf_rpc_port: int = int(
        _NETWORK.get("msfRpcPort")
        or _PORTS.get("msfRpc", _FALLBACK_MSF_RPC_PORT)
    )
    gvm_min_ram_gb: int = int(
        _NETWORK.get("gvmMinRamGb", _FALLBACK_GVM_MIN_RAM_GB)
    )
    findings_service_url: str = str(
        _NETWORK.get("findingsServiceUrl", _FALLBACK_FINDINGS_URL)
    )
    # MVP: without /dev/kvm, provision fails unless this flag is set.
    allow_slow_emulator: bool = False
    mcp_mobile_cmd: str = ""
    mcp_network_cmd: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
