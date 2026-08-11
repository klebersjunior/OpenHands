# Spec Técnica — PROJETOSIN-198: Runtime Rede (mcp-network)

**ADR:** docs/adrs/0001-plataforma-pentest-ia-extensao-openhands.md (accepted) — blueprint §5.2 / §6.3  
**Card Plane:** PROJETOSIN-198 — `6dd9b4fb-5514-492a-8eb1-097f485fdc9b`  
**Agentes:** backend (lead) + devops (compose/runtime image)  
**Prioridade:** P1 — paralelo a 197 se escopo de arquivos isolado  
**Base git:** `e32b31018`  
**Branch:** `feat/fase4-mcp-network-198`  
**Worktree:** `.tmp/worktrees/198`  
**PR target:** fork `klebersjunior/OpenHands` only

---

## Objetivo

Materializar o runtime de **Rede** do engagement: MCP server **`mcp-network`** (nmap, OpenVAS/GVM, Metasploit RPC) + template compose EngMgr, com escopo fail-closed, autonomia server-side e achados no Findings Service.

Pode **paralelizar com 197** — não depende do adapter PentestAgent; só do padrão shared MCP já em main. Integração com orquestrador (196) via tools MCP + capability, não via import interno de `mcp-engine`.

---

## Premissas

1. Reusar `services/mcp-servers/shared/` (mesmo padrão recon/webscan/mobile).
2. Template existente `compose-network-runtime.yml.j2` é esqueleto — expandir com serviços reais (ou sidecars) **sem** host network / privileged desnecessário.
3. Metasploit e GVM são **intrusivos** por default → confirmation gate em manual/semi.
4. Nunca embutir exploits/PoCs no repositório como payloads ofensivos reutilizáveis; tools orquestram RPC/CLI allowlisted. Testes usam mocks/fixtures JSON.
5. Achados → Findings master (`source_tool`: `nmap` \| `openvas` \| `metasploit` \| …).

---

## Contrato MCP

### Tools

| Tool | Args | Intrusivo? | Capability |
|---|---|---|---|
| `net_nmap_scan` | `{ targets[], profile: "discovery"\|"safe"\|"full", ports? }` | `full` = sim | `pentest.scan.passive` (discovery/safe); `pentest.scan.active` (full) |
| `net_gvm_start_scan` | `{ targets[], config_id? }` | sim | `pentest.scan.active` |
| `net_gvm_get_report` | `{ scan_id }` | não | `pentest.scan.active` ou `pentest.findings.view` |
| `net_msf_rpc_execute` | `{ module, options }` | sim | `pentest.exploit.active` |
| `net_msf_session_list` | — | não | `pentest.exploit.active` |

`targets[]` validados com `assert_in_scope` **antes** de qualquer spawn/RPC.

### Profiles nmap

| profile | Flags (conceitual) | Gate |
|---|---|---|
| `discovery` | ping/syn limitados, top ports seguros | livre em semi+ |
| `safe` | version detect leve, sem scripts agressivos | livre em semi+ |
| `full` | scripts/UDP amplos | confirmation em semi; capability active |

### Metasploit RPC

- Cliente RPC contra host **interno** do compose (`MSF_RPC_HOST` / port / token env).
- Allowlist de módulos prefix (`auxiliary/`, `scanner/`, subset `exploit/` documentado) — rejeitar módulo fora da lista → `module_not_allowed`.
- Proibir `setg` / console livre / `execute` shell arbitrário no MVP.
- Output truncado; sessions listadas sem dump de credencial em clear no tool result (redact).

### OpenVAS/GVM

- Cliente HTTP/GMP contra serviço interno; credenciais só env.
- Se imagem GVM for pesada demais para CI: adapter com **modo stub** (`MCP_NETWORK_USE_REAL_BINARIES=0` default em testes) + contrato estável.

---

## Layout

```
services/mcp-servers/
  mcp-network/
    server.py
    pyproject.toml
    tools/
      nmap_scan.py
      gvm_scan.py
      gvm_report.py
      msf_rpc.py
    clients/
      nmap_runner.py
      gvm_client.py
      msf_rpc_client.py
    fixtures/                 # XML/JSON sample para normalize
    tests/
      test_tools_contract.py
      test_scope_and_gates.py
      test_msf_allowlist.py
services/engagement-manager/app/templates/
  compose-network-runtime.yml.j2   # nmap-capable runtime + gvm? + msfrpcd
config/defaults.json               # pentest.network.* image pins / ports
services/mcp-servers/README.md     # + capability pentest.network / env
```

### Capability

Adicionar (espelhar TS + Python):

- `pentest.network.scan` — attach do server + nmap discovery/safe  
  **OU** reutilizar `pentest.scan.passive` / `pentest.scan.active` / `pentest.exploit.active` sem nova cap se Tech Lead preferir menor churn — **preferência MVP:** reutilizar caps existentes (passive/active/exploit) e documentar mapeamento na README; só introduzir `pentest.network.scan` se o frontend/RBAC já tiver buraco claro.

Decisão fechada nesta spec: **reutilizar** `pentest.scan.passive` / `pentest.scan.active` / `pentest.exploit.active` (sem nova literal obrigatória). Launcher anexa `PENTEST_MCP_NETWORK_CMD` se perfil tiver `pentest.scan.passive`.

---

## Compose (DevOps)

Expandir `compose-network-runtime.yml.j2`:

- Serviço runtime com binários nmap (image pin) **ou** sidecar `network-tools`.
- Serviço `gvm` / `gvmd` — opcional via compose profile `gvm` (documentar RAM mínima; default off em dev leve).
- Serviço `msfrpcd` — profile `msf`; bind **só** rede interna do engagement.
- Env: `PENTEST_SCOPE_ALLOWLIST`, `PENTEST_AUTONOMY_MODE`, Findings URL/key, `ENGAGEMENT_ID`.
- Sem `network_mode: host`. Sem montar Docker socket.

---

## Env

| Variable | Purpose |
|----------|---------|
| `PENTEST_MCP_NETWORK_CMD` | stdio launch |
| `MCP_NETWORK_USE_REAL_BINARIES` | `1` para nmap/msf reais |
| `NMAP_BIN` | optional path |
| `GVM_URL` / `GVM_USER` / `GVM_PASSWORD` | GMP/HTTP (secrets env) |
| `MSF_RPC_HOST` / `MSF_RPC_PORT` / `MSF_RPC_TOKEN` | RPC interno |
| `PENTEST_SCOPE_ALLOWLIST` | fail-closed |
| `PENTEST_AUTONOMY_MODE` | server-side |
| `FINDINGS_SERVICE_URL` / `SESSION_API_KEY` | findings |

Estender `ACTIVE_TOOLS` em `confirmation.py` com: `net_nmap_scan` (quando profile full), `net_gvm_start_scan`, `net_msf_rpc_execute`.

---

## AC testáveis

| ID | Critério |
|---|---|
| AC-198-1 | Target fora allowlist → `scope_violation` em todas as tools mutantes |
| AC-198-2 | `net_nmap_scan` profile `full` em semi sem token → `confirmation_required` |
| AC-198-3 | Módulo MSF fora allowlist → `module_not_allowed` |
| AC-198-4 | Fixture nmap/GVM → `normalize_finding` + post mock Findings |
| AC-198-5 | Compose template renderiza sem host network; profiles gvm/msf documentados |
| AC-198-6 | CI verde sem demônios GVM/MSF reais |

---

## Gates

| Gate | Foco |
|---|---|
| **AppSec (crítico)** | Escopo, MSF module allowlist, RPC bind interno, secrets, confirmation, sem Docker socket |
| QA | AC-198-* |
| Design | N/A |

---

## Fora de escopo

- Orquestrador playbooks (196)
- mcp-engine adapters (197)
- Farm / K8s
- Escrita de exploits/PoCs no repo

---

## Entrega

1. Worktree 198 · PR fork `Plane: PROJETOSIN-198`  
2. Comentário Plane com PR URL  
3. AppSec crítico antes do merge
