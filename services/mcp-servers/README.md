# MCP Servers — Pentest (PROJETOSIN-187 / 189 / 190 / 197 / 198)

stdio MCP servers for offensive runtimes. **ADR-0001**.

```
services/mcp-servers/
├── shared/          # findings client, session auth, confirmation, normalize/scope
├── mcp-recon/       # subfinder / httpx / reconftw
├── mcp-webscan/     # ZAP / Nuclei / Wapiti / Nikto / sqlmap
├── mcp-sast/        # Semgrep + Trivy (PROJETOSIN-189)
├── mcp-mobile/      # MobSF + ADB/Frida/apktool/jadx (PROJETOSIN-190)
├── mcp-engine/      # PentestAgent / CAI phase engines (PROJETOSIN-197)
└── mcp-network/     # nmap / GVM(OpenVAS) / Metasploit RPC (PROJETOSIN-198)
```

## Capabilities

| Server / tools | Capability |
|----------------|------------|
| `mcp-recon` (all) | `pentest.recon.run` |
| webscan passive (spider, passive ZAP, nuclei default, wapiti, nikto) | `pentest.scan.passive` |
| webscan active (`web_zap_active_scan`, `web_sqlmap_run`, nuclei intrusive) | `pentest.scan.active` |
| `mcp-sast` (Semgrep / Trivy) | `pentest.sast.run` |
| `mcp-mobile` (MobSF / ADB / Frida / apktool / jadx) | `pentest.mobile.dynamic` |
| `mcp-engine` (`engine_*`, recon/scan/analyze) | `pentest.scan.passive` (minimum to attach) |
| `mcp-engine` phase `exploit` | `pentest.exploit.active` + confirmation in manual/semi |
| `mcp-network` nmap `discovery`/`safe` | `pentest.scan.passive` |
| `mcp-network` nmap `full`, GVM start/report | `pentest.scan.active` |
| `mcp-network` Metasploit RPC execute / sessions | `pentest.exploit.active` |

Session registration should only attach a server when the authenticated profile
has the minimum capability (Fase 0 RBAC). Without `pentest.mobile.dynamic`, the
launcher must **not** attach `PENTEST_MCP_MOBILE_CMD`. Without
`pentest.scan.passive`, do **not** attach `PENTEST_MCP_ENGINE_CMD` or
`PENTEST_MCP_NETWORK_CMD`.

## Environment

| Variable | Purpose |
|----------|---------|
| `SESSION_API_KEY` | Sent as `X-Session-API-Key` to Findings Service |
| `FINDINGS_SERVICE_URL` | Default `http://findings-service:8000` |
| `PENTEST_SCOPE_ALLOWLIST` | CSV of hosts/CIDRs (fail-closed if empty) |
| `PENTEST_WORKSPACE_DIR` | Workspace root for path guard (default `/workspace/project`) |
| `PENTEST_AUTONOMY_MODE` | Server-side only: `manual` \| `semi_autonomous` \| `autonomous` (default semi). Never taken from agent tool args. |
| `OPENHANDS_CONFIRMATION_TOKEN` | Optional env token after UI approval |
| `PENTEST_MCP_RECON_CMD` | Override launch command for mcp-recon |
| `PENTEST_MCP_WEBSCAN_CMD` | Override launch command for mcp-webscan |
| `PENTEST_MCP_SAST_CMD` | Override launch command for mcp-sast |
| `PENTEST_MCP_MOBILE_CMD` | Override launch command for mcp-mobile |
| `PENTEST_MCP_ENGINE_CMD` | Override launch command for mcp-engine |
| `PENTEST_MCP_NETWORK_CMD` | Override launch command for mcp-network |
| `PENTEST_ENGINE_CAI_ENABLED` | `true` to expose CAI in `engine_list_engines` (default off) |
| `PENTEST_ENGINE_PENTESTAGENT_URL` / `_CONTAINER` | Internal control plane for PentestAgent (not host loopback) |
| `PENTEST_ENGINE_CAI_URL` | Internal control plane for CAI when enabled |
| `PENTEST_ENGINE_URL_ALLOWLIST` | CSV of allowed engine control-plane **hostnames** (compose DNS). Fail-closed when empty; loopback/link-local/metadata always rejected |
| `PENTEST_ENGINE_MOCK` | `1` (default when URL unset) — unit/CI path without Docker engine images |
| `PENTEST_ENGINE_LLM_BASE_URL` / `LITELLM_BASE_URL` | Enterprise LiteLLM only — Ollama / `localhost:11434` / `OLLAMA_*` rejected (`self_hosted_llm_forbidden`) |
| `PENTEST_CAPABILITIES` | Optional CSV of profile capabilities for tool-level RBAC |
| `ENGAGEMENT_ID` | Correlation id for engine runs / findings |
| `MOBSF_URL` | MobSF base URL (e.g. `http://mobsf:8000`); required for MobSF tools |
| `MOBSF_API_KEY` | MobSF API key (env only; never hardcoded) |
| `ADB_HOST` | Generic ADB endpoint host (default `android-emulator`) |
| `ADB_PORT` | Generic ADB endpoint port (default `5555`) |
| `PENTEST_ADB_TARGET` | `emulator` (default) \| `physical` — when `physical`, Desktop injects `ADB_HOST=host.docker.internal` (Opção B / PROJETOSIN-194) so mcp-mobile keeps one ADB adapter |
| `MCP_WEBSCAN_TIMEOUT_SEC` | Timeout for intrusive web tools (default 300) |
| `MCP_MOBILE_USE_REAL_BINARIES` | Set `1` to invoke real `adb`/`apktool`/`jadx`/`frida` |
| `MCP_NETWORK_USE_REAL_BINARIES` | Set `1` for real nmap / GVM / msfrpcd (default `0` — stub fixtures for CI) |
| `NMAP_BIN` | Optional path to nmap |
| `GVM_URL` / `GVM_USER` / `GVM_PASSWORD` | Internal GVM/GMP HTTP bridge (secrets env-only) |
| `MSF_RPC_HOST` / `MSF_RPC_PORT` / `MSF_RPC_TOKEN` | Internal Metasploit RPC (token/password env-only) |
| `DEFECTDOJO_API_URL` | One-way DefectDojo mirror base URL |
| `DEFECTDOJO_API_TOKEN` | DefectDojo API token |
| `DEFECTDOJO_PRODUCT_TYPE_DEFAULT` | Default product type (e.g. `Pentest`) |
| `DEFECTDOJO_VERIFY_TLS` | TLS verify for DefectDojo (`true`/`false`) |
| `DEFECTDOJO_DRY_RUN` | `1` to skip real DefectDojo writes |

## Local run

```bash
# from repo root — PYTHONPATH must include services/mcp-servers
export PYTHONPATH=services/mcp-servers:services/mcp-servers/mcp-recon
export PENTEST_SCOPE_ALLOWLIST=example.com
export SESSION_API_KEY=dev-key
export FINDINGS_SERVICE_URL=http://127.0.0.1:18002
python services/mcp-servers/mcp-recon/server.py

export PYTHONPATH=services/mcp-servers:services/mcp-servers/mcp-webscan
python services/mcp-servers/mcp-webscan/server.py

export PYTHONPATH=services/mcp-servers:services/mcp-servers/mcp-sast
export PENTEST_WORKSPACE_DIR=/workspace/project
python services/mcp-servers/mcp-sast/server.py

export PYTHONPATH=services/mcp-servers:services/mcp-servers/mcp-mobile
export MOBSF_URL=http://mobsf:8000
export MOBSF_API_KEY=dev-mobsf-key
export ADB_HOST=android-emulator
export ADB_PORT=5555
python services/mcp-servers/mcp-mobile/server.py

export PYTHONPATH=services/mcp-servers:services/mcp-servers/mcp-engine
export ENGAGEMENT_ID=00000000-0000-0000-0000-000000000001
export PENTEST_ENGINE_MOCK=1
python services/mcp-servers/mcp-engine/server.py

export PYTHONPATH=services/mcp-servers:services/mcp-servers/mcp-network
export MCP_NETWORK_USE_REAL_BINARIES=0
python services/mcp-servers/mcp-network/server.py
```

## Register with Agent Canvas / Agent Server

Until workspace-type hooks auto-register MCP for `pentest` workspaces, set
stdio commands via settings / MCP API or env:

```bash
PENTEST_MCP_RECON_CMD='python /opt/mcp-servers/mcp-recon/server.py'
PENTEST_MCP_WEBSCAN_CMD='python /opt/mcp-servers/mcp-webscan/server.py'
PENTEST_MCP_SAST_CMD='python /opt/mcp-servers/mcp-sast/server.py'
PENTEST_MCP_MOBILE_CMD='python /opt/mcp-servers/mcp-mobile/server.py'
PENTEST_MCP_ENGINE_CMD='python /opt/mcp-servers/mcp-engine/server.py'
PENTEST_MCP_NETWORK_CMD='python /opt/mcp-servers/mcp-network/server.py'
```

Example `config.toml` fragment (engagement):

```toml
[mcp.mcp-recon]
command = "python"
args = ["/opt/mcp-servers/mcp-recon/server.py"]

[mcp.mcp-webscan]
command = "python"
args = ["/opt/mcp-servers/mcp-webscan/server.py"]

[mcp.mcp-sast]
command = "python"
args = ["/opt/mcp-servers/mcp-sast/server.py"]

[mcp.mcp-mobile]
command = "python"
args = ["/opt/mcp-servers/mcp-mobile/server.py"]

[mcp.mcp-engine]
command = "python"
args = ["/opt/mcp-servers/mcp-engine/server.py"]

[mcp.mcp-network]
command = "python"
args = ["/opt/mcp-servers/mcp-network/server.py"]
```

## mcp-engine contract (PROJETOSIN-197)

Stable tools for orchestrator (196):

| Tool | Purpose |
|------|---------|
| `engine_list_engines` | `{ engines: [{ id, status, capabilities[] }] }` |
| `engine_start_phase` | `{ engine_id, phase, playbook_id?, targets?, options? }` → `{ run_id, status }` |
| `engine_get_run` | Poll `{ run_id, engine_id, phase, status, summary?, finding_ids[] }` |
| `engine_cancel_run` | Best-effort cancel |
| `engine_list_playbooks` | MVP catalog stubs (`web-blackbox-recon`, `web-scan-passive`, …) |

Canonical phases: `recon` → `scan` → `analyze` → `exploit` (aliases:
`enumeration`→`scan`, `exploitation`→`exploit`). Achados always go through
`normalize_finding` + Findings Service (never DefectDojo direct). LLM for
motors: LiteLLM → enterprise providers only (Ollama/self-hosted rejected).

Optional compose: `services/engagement-manager/app/templates/compose-engine-runtime.yml.j2`
(image pins in `config/defaults.json` → `images.pentestAgent` / `images.cai` and
`pentest.engines.*`).

## Confirmation gate (stub)

Intrusive tools (`zap_active_scan`, `sqlmap_run`, `nuclei_intrusive`,
`mobsf_dynamic`, `adb_install`, `adb_shell_mutant`, `frida_attach`,
`engine_exploit`, `net_nmap_scan` when profile=`full`, `net_gvm_start_scan`,
`net_msf_rpc_execute`) in `semi_autonomous` mode return:

```json
{"ok": false, "error": "confirmation_required", "request_id": "..."}
```

Approve via `shared.confirmation.approve_confirmation(request_id)` (test/stub)
or set `OPENHANDS_CONFIRMATION_TOKEN` / pass `confirmation_token` on re-run.

## MobSF sidecar

Compose fragment (internal network only — no host port publish in production):
`docker/runtimes/mobile/compose.mobsf.fragment.yml`. Emulator lifecycle is
PROJETOSIN-191; UI/upload proxy is PROJETOSIN-192.

## Physical device (PROJETOSIN-194) — Opção B

`mcp-mobile` always talks to a **generic** ADB TCP endpoint (`ADB_HOST` /
`ADB_PORT`). Electron IPC (PROJETOSIN-193) only discovers/connects devices on
the **host**; it does **not** replace mcp-mobile or expose `adb shell` /
`install` to the renderer.

When conversation metadata sets `pentest_adb_target=physical`:

1. Desktop injects `ADB_HOST=host.docker.internal` (Docker Desktop) or the host
   gateway IP into the engagement runtime env (no full compose recreate required
   when env override is enough).
2. Host `adb` keeps the USB/LAN device online; runtime reaches it through the
   published ADB port on the host.
3. Linux without the DNS alias: add
   `extra_hosts: ["host.docker.internal:host-gateway"]` or set `ADB_HOST` to
   the docker0 gateway IP.

Default `PENTEST_ADB_TARGET=emulator` keeps `ADB_HOST=android-emulator`.

## Network runtime (PROJETOSIN-198)

Compose template: `services/engagement-manager/app/templates/compose-network-runtime.yml.j2`.

- Default stack: nmap-capable `runtime-network` (no host network, no Docker socket).
- Compose profile `gvm`: optional Greenbone/GVM sidecar (heavy; ~8GB+ RAM).
- Compose profile `msf`: `msfrpcd` on the **internal** engagement network only.
- Metasploit modules are allowlisted (`auxiliary/`, `scanner/`, documented
  `exploit/` prefixes). Free console / `setg` / arbitrary shell options are rejected.
- CI uses `MCP_NETWORK_USE_REAL_BINARIES=0` (fixtures) — no live GVM/MSF daemons.

## Tests

```bash
cd services/mcp-servers/mcp-recon && PYTHONPATH=..:. pytest -q
cd ../mcp-webscan && PYTHONPATH=..:. pytest -q
cd ../mcp-sast && PYTHONPATH=..:. pytest -q
cd ../mcp-mobile && PYTHONPATH=..:. pytest -q
cd ../mcp-engine && PYTHONPATH=..:. pytest -q
cd ../mcp-network && PYTHONPATH=..:. pytest -q
```
