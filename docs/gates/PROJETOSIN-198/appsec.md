---
card: PROJETOSIN-198
pr: 17
veredicto: PASS
agente: appsec
data: 2026-08-10
tip: 15d4d1d447af60ef80d9b8f3a8ef565cfcb93d64
ci: npm-audit-high-clean; pytest mcp-network (declarado no PR); ac198 compose asserts
repo: klebersjunior/OpenHands
branch: feat/fase4-mcp-network-198
---

# AppSecurity — PROJETOSIN-198 (mcp-network runtime)

**Veredicto:** PASS

**Revisor:** AppSec gate (agente ≠ autor da implementação; não assina QA/Design). Review formal no PR #17.

## Escopo

Spec `docs/specs/fase-4/198-mcp-network-runtime.md` — gate **crítico**:

1. Escopo fail-closed em tools mutantes
2. Confirmation: nmap `full`, GVM start, MSF execute (semi/manual)
3. MSF module allowlist + rejeição console/setg/shell livre
4. RPC/GVM só rede interna; sem host network / docker.sock
5. Secrets só env; redaction em sessions
6. Sem exploits/PoCs versionados
7. Achados → Findings master

Worktree `.tmp/worktrees/198` @ tip `15d4d1d447af60ef80d9b8f3a8ef565cfcb93d64`. PR #17.

## Checklist

- [x] Sem segredos de produção hardcoded (GVM_*/MSF_RPC_* via env; dry-run tokens só fixture EngMgr)
- [x] `npm audit --audit-level=high` sem high/critical (4 moderate pré-existentes: dompurify/electron — fora do delta 198)
- [x] Escopo: `assert_targets_in_scope` / `assert_in_scope` antes de spawn/RPC; allowlist vazia → `scope_violation`
- [x] Confirmation: `ACTIVE_TOOLS` inclui `net_nmap_scan` / `net_gvm_start_scan` / `net_msf_rpc_execute`; nmap só chama gate em `profile=full`
- [x] MSF allowlist (`auxiliary/`, `scanner/`, subset `exploit/…`); `module_not_allowed` fora da lista; options `setg`/`console`/`shell`/… rejeitadas
- [x] Compose network: sem `network_mode: host`, sem `docker.sock`, sem `ports:`; `internal: true` no bridge interno; GVM/MSF só `network_internal`
- [x] Fixtures nmap/GVM = XML/JSON de amostra (sem payloads ofensivos reutilizáveis)
- [x] Findings: nmap/GVM → `FindingsClient.post_finding` (`source_tool` `nmap` / `openvas`); sem sink local alternativo

## Asserções positiváveis (tornáveis vácuas se o controle sumir)

| ID | Se o controle for removido, o teste/asserção falha |
|---|---|
| A1 | `test_ac_198_1_out_of_scope_all_mutating_tools` — nmap/GVM/MSF → `scope_violation`; zero posts Findings |
| A2 | `test_ac_198_1_empty_allowlist_fail_closed` — allowlist ausente → `scope_violation` |
| A3 | `test_ac_198_2_nmap_full_requires_confirmation` — `full` sem token → `confirmation_required` + zero posts |
| A4 | `test_gvm_and_msf_require_confirmation_in_semi` — GVM start / MSF execute → `confirmation_required` |
| A5 | `test_ac_198_3_*` — módulo fora allowlist → `module_not_allowed`; escapes `..` / `;` rejeitados |
| A6 | `test_forbidden_option_keys` — `setg` / `shell` options → erro |
| A7 | `test_msf_sessions_redact_credentials` — `password` → `[REDACTED]` |
| A8 | `test_ac198_network_compose_profiles_no_host_network` — render sem `network_mode: host` / `docker.sock` / `ports:`; profiles `gvm`/`msf`; `internal: true` |
| A9 | `test_ac_198_tools_exposed` — schema MCP **sem** `autonomy_mode` (autonomia só `PENTEST_AUTONOMY_MODE`) |

## Findings

### Critical / High

Nenhum. **Sem bloqueio.**

### MEDIUM — Redaction de sessions por chave exata

`redact_value` só mascara se `key.lower() in _REDACT_KEYS` (ex. `password`, `token`). Chaves compostas (`smb_password`, `cleartext_password`, `DBPassword`) passam intactas no tool result de `net_msf_session_list`.

**Decisão:** residual MEDIUM. Controle atual cobre o stub e chaves canônicas; endurecer com substring/`*_password` em follow-up sem ampliar superfície de false-positive em títulos.

### MEDIUM — `MSF_RPC_HOST` / `GVM_URL` sem pin de hostname interno

Cliente HTTP usa o host/URL do env sem allowlist de nomes do compose (`{project}-msfrpcd`, `{project}-gvm`). Provisioner injeta endpoints internos; override hostil de env no runtime poderia apontar o token/Basic Auth para destino externo (exfil).

**Decisão:** residual MEDIUM — aceitável no MVP com compose pinned; follow-up: validar host contra sufixo do projeto / bloquear IPs não-RFC1918 se desejado.

### LOW — `ports` do nmap sem charset allowlist

`build_nmap_args` passa `ports` como argv único a `-p` via `create_subprocess_exec` (sem shell). Injeção de shell mitigada; defesa em profundidade poderia restringir a `[0-9,/\-T:]+`.

### LOW — Prefixo `auxiliary/` amplo (aceito pela spec)

Allowlist de orquestração cobre toda a árvore `auxiliary/` / `scanner/` + subset `exploit/`. Risco residual de módulos DOS/intrusivos mitiga-se por escopo + confirmation — alinhado à spec § Metasploit RPC.

### LOW — `source_tool: metasploit` registrado, execute não posta Findings

`SOURCE_TOOLS` inclui `metasploit`; `net_msf_rpc_execute` devolve resultado truncado/redacted sem `post_finding`. Achados ofensivos MSF no MVP ficam no tool result (não em sink paralelo). AC-198-4 cobre nmap/GVM. Sem vazamento para disco local.

## Controles verificados (mapeamento gate crítico)

| Controle | Evidência |
|---|---|
| Escopo fail-closed | `tools/nmap_scan.py`, `gvm_scan.py`, `msf_rpc.py` + `shared/normalize.assert_in_scope` |
| Confirmation ACTIVE_TOOLS | `shared/confirmation.py` + gates condicionais (nmap só `full`) |
| MSF allowlist / anti-console | `clients/msf_rpc_client.py` `assert_module_allowed` / `assert_options_safe` |
| Bind interno / sem sock | `compose-network-runtime.yml.j2` + `test_ac198_network_compose_*` |
| Secrets env | `GVM_*` / `MSF_RPC_*`; provisioner `secrets.token_urlsafe` (dry-run tokens só teste) |
| Sem PoCs no repo | fixtures XML/JSON; allowlist = paths de módulo, sem bodies |
| Findings master | `FindingsClient` em nmap/GVM report; transport mock nos testes AC-198-4 |

## Dependências

`npm audit --audit-level=high`: **PASS** (0 high/critical). Moderates pré-existentes — fora do delta 198 (Python MCP + EngMgr template).

## Ação requerida

Nenhuma para merge AppSec. Residuais MEDIUM → backlog (redaction substring; pin de host RPC/GVM) sem bloquear 198.

**Não mergeado por AppSec.** Tech Lead decide merge somente com QA+AppSec PASS (Design N/A).
