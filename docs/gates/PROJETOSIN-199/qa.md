---
card: PROJETOSIN-199
pr: 18
veredicto: PASS
agente: qa
data: 2026-08-10
tip: 0c577e069
ci: pytest-shared-ac199+pytest-findings-full
repo: klebersjunior/OpenHands
branch: feat/fase4-observability-199
appsec: PASS @ 0c577e069
---

# QA — PROJETOSIN-199 (SigNoz OTEL + chain of custody)

**Veredicto:** PASS

**Revisor:** QA gate (papel ≠ autor da implementação; não assina AppSec/Design). Review formal no PR #18.

Spec: `docs/specs/fase-4/199-observability-signoz-custody.md` · ADR-0001  
PR: https://github.com/klebersjunior/OpenHands/pull/18 · tip `0c577e069` (feat `1b5a51a61` + AppSec laudo)  
Worktree: `.tmp/worktrees/199`

AppSec pré-condição: **PASS** (`docs/gates/PROJETOSIN-199/appsec.md`) — não reassinado por QA.

## Critérios de aceite

| AC | Status | Evidência |
|----|--------|-----------|
| **AC-199-1** Sem OTLP: no-op; app/setup ok | **PASS** | `services/shared/tests/test_otel_noop.py` — `otel_enabled()` false sem endpoint; `setup_otel(..., force=True)` + `emit_event` sem crash; disable explícito com endpoint+`PENTEST_OTEL_ENABLED=false` |
| **AC-199-2** Redaction session/Authorization | **PASS** | `tests/test_redaction.py` — `Authorization`, `X-Session-API-Key`, `api_key`, `password`, cookie aninhado e bearer inline → `[REDACTED]`; attrs seguros intactos |
| **AC-199-3** Custody hash chain tamper-evident | **PASS** | Unit: `test_custody_hash.py` (`verify_chain` True → False após mutar metadata do meio). API: `findings-service/tests/test_custody_chain.py::test_ac_199_3_custody_api_chain` — 3 appends + list + tamper `action` quebra chain; metadata `Authorization` redacted na persistência |
| **AC-199-4** `scope_violation` nome canônico | **PASS** | `test_scope_violation_event.py` — `InMemorySpanExporter`; span `pentest.scope.violation` + `error_code=scope_violation` ao `assert_in_scope` fora da allowlist |
| **AC-199-5** Finding create → `pentest.finding.mutate` | **PASS** | `test_ac_199_5_finding_create_emits_mutate_span` — POST finding 201; span canônico com `action=create` + `finding.id`; custody total ≥ 1 |
| **AC-199-6** `.env.sample` + `defaults.json`; sem secrets | **PASS** | `test_otel_config_docs.py` + inspeção: `pentest.otel.exporterOtlpEndpoint=""`, `llmBodies=false`; vars OTEL/`PENTEST_OTEL_*`/`ENGAGEMENT_ID` documentadas em `.env.sample`; headers só em comentário sem valor |

## Regressão

| Checagem | Resultado |
|----------|-----------|
| `pytest services/shared/tests/test_otel_*.py test_redaction.py test_custody_hash.py test_scope_violation_event.py` | **PASS** — 6/6 |
| `pytest services/findings-service/tests/test_custody_chain.py` | **PASS** — 2/2 |
| `pytest services/findings-service/tests/` (suite completa) | **PASS** — 21/21 (CRUD/triage/DD sync + custody) |
| npm lint/test/build | **N/A** — delta Python/services + docs/config; sem UI Canvas |
| E2E mock-LLM | **N/A** — fora do mapping; card ops/backend |
| Design gate | **N/A** (spec) |
| AppSec gate | **PASS** (pré-condição; não reassinado) |

## Asserções falsificáveis

| Asserção | Como falharia se controle ausente | Resultado |
|----------|-----------------------------------|-----------|
| No-op sem endpoint | `otel_enabled()` true / setup crash → AC-199-1 falha | PASS |
| Redaction Authorization/session | valor secreto sobra em mapping → AC-199-2 falha | PASS |
| Tamper mid-chain | `verify_chain` permanece True → AC-199-3 falha | PASS |
| Nome canônico scope | span ausente / nome diferente → AC-199-4 falha | PASS |
| Finding mutate span | lista de spans sem `pentest.finding.mutate` → AC-199-5 falha | PASS |
| Docs sem header secreto | assignment não-vazio de `OTEL_EXPORTER_OTLP_HEADERS` → AC-199-6 falha | PASS |

## Residual (não bloqueante)

- AppSec LOW: trecho `or True` em `test_otel_config_docs.py` vacua uma checagem auxiliar de `signoz-ingestion-key=`; a checagem forte de linhas `OTEL_EXPORTER_OTLP_HEADERS=` não-vazias permanece. Não rebaixa AC-199-6.
- Residuais AppSec MEDIUM (redaction MCP helper; ownership custody; `/internal` append) — backlog, fora do escopo de bloqueio QA AC.

## Ação requerida

Nenhuma. **Não mergeado por QA.** Tech Lead: merge só com QA+AppSec PASS (Design N/A).
