"""AC-198-3 — Metasploit module allowlist."""

from __future__ import annotations

import json

import pytest

from clients.msf_rpc_client import (
    MSF_ALLOWED_EXPLOIT_PREFIXES,
    MSF_ALLOWED_PREFIXES,
    MsfModuleNotAllowedError,
    assert_module_allowed,
    assert_options_safe,
)
from shared.confirmation import approve_confirmation
from tests.conftest import ENGAGEMENT_ID


def test_allowlist_accepts_documented_prefixes():
    assert assert_module_allowed("auxiliary/scanner/http/http_version") == (
        "auxiliary/scanner/http/http_version"
    )
    assert assert_module_allowed("scanner/portscan/tcp") == "scanner/portscan/tcp"
    # Documented exploit subset
    assert any(p.startswith("exploit/") for p in MSF_ALLOWED_EXPLOIT_PREFIXES)
    assert assert_module_allowed("exploit/multi/handler") == "exploit/multi/handler"
    assert assert_module_allowed(
        "exploit/windows/smb/ms17_010_eternalblue"
    ).startswith("exploit/windows/smb/")


def test_ac_198_3_rejects_unknown_module():
    with pytest.raises(MsfModuleNotAllowedError) as exc:
        assert_module_allowed("exploit/windows/local/bypassuac_fodhelper")
    assert exc.value.code == "module_not_allowed"

    with pytest.raises(MsfModuleNotAllowedError):
        assert_module_allowed("post/multi/gather/env")


def test_rejects_path_traversal_and_console_escapes():
    with pytest.raises(MsfModuleNotAllowedError):
        assert_module_allowed("../etc/passwd")
    with pytest.raises(MsfModuleNotAllowedError):
        assert_module_allowed("auxiliary/scanner/http/x;rm -rf /")


def test_forbidden_option_keys():
    with pytest.raises(Exception):
        assert_options_safe({"setg": "LHOST=1.2.3.4"})
    with pytest.raises(Exception):
        assert_options_safe({"shell": "id"})
    assert assert_options_safe({"RHOSTS": "10.0.0.5", "RPORT": 445})["RHOSTS"] == (
        "10.0.0.5"
    )


@pytest.mark.asyncio
async def test_ac_198_3_tool_returns_module_not_allowed():
    from tools.msf_rpc import run_msf_rpc_execute

    # Approve confirmation so we reach the allowlist check.
    first = json.loads(
        await run_msf_rpc_execute(
            module="exploit/windows/local/bypassuac_fodhelper",
            options={"RHOSTS": "10.0.0.5"},
            engagement_id=ENGAGEMENT_ID,
        )
    )
    assert first["error"] == "confirmation_required"
    token = approve_confirmation(first["request_id"])

    second = json.loads(
        await run_msf_rpc_execute(
            module="exploit/windows/local/bypassuac_fodhelper",
            options={"RHOSTS": "10.0.0.5"},
            engagement_id=ENGAGEMENT_ID,
            confirmation_token=token,
        )
    )
    assert second["ok"] is False
    assert second["error"] == "module_not_allowed"


@pytest.mark.asyncio
async def test_allowlisted_module_executes_in_stub():
    from tools.msf_rpc import run_msf_rpc_execute

    first = json.loads(
        await run_msf_rpc_execute(
            module="auxiliary/scanner/portscan/tcp",
            options={"RHOSTS": "10.0.0.5"},
            engagement_id=ENGAGEMENT_ID,
        )
    )
    token = approve_confirmation(first["request_id"])
    body = json.loads(
        await run_msf_rpc_execute(
            module="auxiliary/scanner/portscan/tcp",
            options={"RHOSTS": "10.0.0.5"},
            engagement_id=ENGAGEMENT_ID,
            confirmation_token=token,
        )
    )
    assert body["ok"] is True
    assert body["module"] == "auxiliary/scanner/portscan/tcp"
    assert body["mode"] == "stub"
    assert MSF_ALLOWED_PREFIXES  # documented surface for AppSec
