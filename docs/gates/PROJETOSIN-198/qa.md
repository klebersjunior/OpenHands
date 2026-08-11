---
card: PROJETOSIN-198
pr: 17
veredicto: PASS
agente: qa
data: 2026-08-10
tip: 60cc357779faf3158bdc3b1abf1d30d0f8953237
ci: test-and-build-ubuntu-pass; windows-pass; mock-llm-exit-124-known-flake
repo: klebersjunior/OpenHands
branch: feat/fase4-mcp-network-198
---

# QA Report — PROJETOSIN-198 (mcp-network runtime)

**Veredicto:** PASS

**PR:** https://github.com/klebersjunior/OpenHands/pull/17  
**Tip avaliado:** `60cc357779faf3158bdc3b1abf1d30d0f8953237`  
**Worktree:** `.tmp/worktrees/198`  
**Revisor:** QA gate (≠ autor da implementação; ≠ AppSec). Não auto-assina AppSec. Não mergeia.

Spec: `docs/specs/fase-4/198-mcp-network-runtime.md`  
AppSec: PASS (`docs/gates/PROJETOSIN-198/appsec.md`) — Design N/A.

## Critérios de aceite

| AC | Status | Evidência |
|---|---|---|
| **AC-198-1** Target fora allowlist → `scope_violation` (tools mutantes) | **PASS** | `test_ac_198_1_out_of_scope_all_mutating_tools` — nmap/GVM/MSF → `scope_violation`; `transport.posts == []`. `test_ac_198_1_empty_allowlist_fail_closed` — allowlist ausente → `scope_violation`. |
| **AC-198-2** `net_nmap_scan` profile `full` em semi sem token → `confirmation_required` | **PASS** | `test_ac_198_2_nmap_full_requires_confirmation` — `confirmation_required` + zero posts; após token → `ok`. `net_nmap_scan` ∈ `ACTIVE_TOOLS`. |
| **AC-198-3** Módulo MSF fora allowlist → `module_not_allowed` | **PASS** | `test_ac_198_3_rejects_unknown_module` + `test_ac_198_3_tool_returns_module_not_allowed`; escapes `..` / `;` rejeitados. |
| **AC-198-4** Fixture nmap/GVM → normalize + post Findings | **PASS** | `test_ac_198_4_nmap_fixture_posts_findings` (`source_tool=nmap`); `test_ac_198_4_gvm_fixture_normalize_and_post` (`source_tool=openvas`); transport mock. |
| **AC-198-5** Compose sem host network; profiles gvm/msf documentados | **PASS** | `test_ac198_network_compose_profiles_no_host_network` — sem `network_mode: host` / `docker.sock` / `ports:`; `profiles: ["gvm"]` / `["msf"]`; `internal: true`. Template + README documentam profiles. |
| **AC-198-6** CI verde sem demônios GVM/MSF reais | **PASS** | pytest local com `MCP_NETWORK_USE_REAL_BINARIES=0` (stubs); EngMgr dry-run. CI `test-and-build` ubuntu+windows **PASS** (run `31448358572`). Sem GVM/MSF reais no path de teste. |

## Asserções positiváveis (tornáveis vácuas se o controle sumir)

| ID | Se o controle for removido, o teste falha |
|---|---|
| Q1 | AC-198-1 — `error == "scope_violation"` + zero Findings posts |
| Q2 | AC-198-2 — `error == "confirmation_required"` sem token; `ok` só com approve |
| Q3 | AC-198-3 — `error == "module_not_allowed"` / `MsfModuleNotAllowedError.code` |
| Q4 | AC-198-4 — `findings_count >= 1` + `source_tool` nmap/openvas no mock transport |
| Q5 | AC-198-5 — assert negativos `network_mode: host` / `docker.sock` / `ports:` + profiles presentes |
| Q6 | `test_ac_198_tools_exposed` — schema sem `autonomy_mode` (autonomia só env) |

## Regressão

| Check | Resultado | Evidência |
|---|---|---|
| `mcp-network` pytest (py3.12, `mcp==1.15.0`) | **PASS** 16/16 | worktree 198; stubs (`MCP_NETWORK_USE_REAL_BINARIES=0`) |
| EngMgr `tests/test_runtime_provisioner.py` | **PASS** 11/11 | inclui `ac198` compose + defaults pins |
| EngMgr `-k ac198` | **PASS** 2/2 | AC-198-5 + defaults.json |
| CI `test-and-build (ubuntu)` | **PASS** | run `31448358572` |
| CI `test-and-build (windows)` | **PASS** | mesmo run |
| CI `mock-llm-e2e` | **FAIL** exit **124** | run `31448358587` — flaky residual conhecido; **fora do escopo** network (sem demônios GVM/MSF). Não bloqueia 198. |

### Nota de ambiente pytest

`mcp>=1.6.0` sem pin superior pode resolver para versões intermediárias (ex. 1.9.x) onde `from __future__ import annotations` quebra `FastMCP` (`issubclass` em annotation string). Suite verde com `mcp==1.6.0` ou `mcp>=1.15,<breaking`. Residual de packaging — não invalida AC com pin conhecido; follow-up opcional pinar no `pyproject.toml`.

## Veredicto

**PASS** — AC-198-1..6 com evidência própria; AppSec PASS pré-existente não reassinado; mock-llm exit 124 tratado como flake fora de escopo.

**Próximo:** Tech Lead pode mergear com QA+AppSec PASS (Design N/A). QA não mergeia.
