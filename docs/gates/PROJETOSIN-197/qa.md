---
card: PROJETOSIN-197
pr: 15
veredicto: PASS
agente: qa
data: 2026-08-10
tip: 2a92b949f
ci: pytest-mcp-engine-45
repo: klebersjunior/OpenHands
branch: feat/fase4-mcp-engine-197
appsec: PASS @ 1555e4e2c / laudo 2a92b949f
---

# QA — PROJETOSIN-197 (mcp-engine PentestAgent / CAI)

**Veredicto:** PASS

**Revisor:** QA gate (papel ≠ autor da implementação `5f02d0748` / fix `1555e4e2c`). Não assina AppSec. Não mergeia.

Spec: `docs/specs/fase-4/197-mcp-engine-pentestagent-cai.md` · ADR-0001  
PR: https://github.com/klebersjunior/OpenHands/pull/15 · tip `2a92b949f` (feat + AppSec fix + AppSec PASS laudo)  
Worktree: `.tmp/worktrees/197`

AppSec pré-condição: **PASS** (`docs/gates/PROJETOSIN-197/appsec.md`) — não reassinado por QA.

## Critérios de aceite

| AC | Status | Evidência |
|----|--------|-----------|
| **AC-197-1** `engine_list_engines` lista `pentestagent`; CAI ausente se flag off | **PASS** | `test_ac_197_1_list_engines_pentestagent_cai_absent_when_flag_off` + `test_ac_197_1_cai_listed_when_enabled` |
| **AC-197-2** target fora allowlist → `scope_violation`; zero spawn útil | **PASS** | `test_ac_197_2_scope_violation_no_spawn` (`posts==[]`); `test_ac_197_2_empty_allowlist_fail_closed` |
| **AC-197-3** fase `exploit` em `semi_autonomous` sem token → `confirmation_required` | **PASS** | `test_ac_197_3_exploit_semi_without_token_confirmation_required`; com token: `test_ac_197_3_exploit_with_token_proceeds` |
| **AC-197-4** achados mock → `normalize_finding` + post Findings | **PASS** | `test_ac_197_4_mock_findings_normalized_and_posted` — keys ⊆ `normalize_finding`; `finding_ids` em `engine_get_run` |
| **AC-197-5** troca `engine_id` não muda schema das tools | **PASS** | `test_ac_197_5_schema_stable_across_engines` + `test_ac_197_5_start_schema_same_for_cai_and_pentestagent` |
| **AC-197-6** unitários verdes sem Docker images reais | **PASS** | `test_ac_197_6_adapters_never_require_docker_images`; suite completa **45 passed** (`PENTEST_ENGINE_MOCK` path) |
| **AC-197-7** README + env; `config.toml` fragment | **PASS** | `services/mcp-servers/README.md` (tabela env + `[mcp.mcp-engine]` + contrato tools); `.env.sample` (`PENTEST_MCP_ENGINE_CMD`, allowlist, CAI); `config/defaults.json` → `images.pentestAgent`/`cai` + `pentest.engines.*` |

## Regressão AppSec HIGH (fail-closed)

| ID | Status | Evidência |
|----|--------|-----------|
| **HIGH-1** targets vazios/None/omitidos | **PASS** | `test_high1_empty_or_omitted_targets_fail_closed` → `invalid_targets`, `posts==[]` |
| **HIGH-2** SSRF engine URL | **PASS** | `test_high2_engine_url_ssrf_rejected` (127.1, metadata, link-local, …); allowlisted host OK; allowlist vazia fail-closed |
| **HIGH-3** Ollama / localhost:11434 | **PASS** | `test_high3_ollama_self_hosted_rejected` → `self_hosted_llm_forbidden`; enterprise LiteLLM permitido |

Filtro local: `pytest -k "high1 or high2 or high3 or ac_197"` → **36 passed**.

## Regressão

| Checagem | Resultado |
|----------|-----------|
| `pytest services/mcp-servers/mcp-engine/tests` | **PASS** — **45/45** (0.52s) @ tip `2a92b949f` |
| npm lint/test/build | **N/A** — delta Python MCP/services + docs/config; sem UI Canvas |
| E2E mock-LLM | **N/A** — fora do mapping (`services/mcp-servers/**`); card backend |
| Design gate | **N/A** (spec) |
| AppSec gate | **PASS** (pré-condição; não reassinado) |

## Asserções falsificáveis

| Asserção | Como falharia se controle ausente | Resultado |
|----------|-----------------------------------|-----------|
| CAI off oculto | `cai` em engines com flag unset → AC-197-1 falha | PASS |
| Escopo fail-closed | out-of-scope retorna ok/spawn → AC-197-2 falha | PASS |
| Exploit confirmation | exploit sem token spawna → AC-197-3 falha | PASS |
| Findings master | post sem shape `normalize_finding` → AC-197-4 falha | PASS |
| Schema estável | props `engine_start_phase` mudam com CAI on → AC-197-5 falha | PASS |
| Sem imagens Docker | adapter exige socket/pull → AC-197-6 falha | PASS |
| Docs MCP engine | README sem `PENTEST_MCP_ENGINE_CMD` / fragment → AC-197-7 falha | PASS |
| HIGH-1 anti-vácuo | `targets=[]` spawna → HIGH-1 falha | PASS |
| HIGH-2 allowlist | `127.1` / metadata passam → HIGH-2 falha | PASS |
| HIGH-3 Ollama | `OLLAMA_HOST=localhost:11434` aceito → HIGH-3 falha | PASS |

## Residual (não bloqueante)

- AppSec MEDIUM-1: nested `options` / chaves LLM ainda forwardáveis ao motor remoto — fora do escopo de bloqueio QA AC.
- AppSec MEDIUM-2 / LOW: alinhamento CSV scope; `engagement_id` fallback — backlog.

## Ação requerida

Nenhuma. **Não mergeado por QA.** Tech Lead: merge só com QA+AppSec PASS (Design N/A).

**[GITHUB-REVIEW-PENDENTE]** se `gh pr review` for bloqueado (conta = autor do PR) — veredicto neste laudo + comentário no PR; pedir review formal APPROVE de conta distinta.
