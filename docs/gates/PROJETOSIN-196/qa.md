---
card: PROJETOSIN-196
pr: 16
veredicto: PASS
agente: qa
data: 2026-08-10
repo: klebersjunior/OpenHands
branch: feat/fase4-orchestrator-196
commit: 51661f67f
ci: lint-test-build-ubuntu-pass; windows-pass; mock-llm-1-flake-settings
design: N/A (TL — UI chips/botões)
appsec: pending (não auto-assinado)
---

# QA Report — PROJETOSIN-196 Orquestrador + playbooks + UI

**Veredicto:** PASS  
**PR:** https://github.com/klebersjunior/OpenHands/pull/16  
**Tip avaliado:** `51661f67fde69e3ea0acef5c5fd6e3d5ce30b085`  
**Worktree:** `.tmp/worktrees/196`  
**Revisor:** QA Agent (evidência própria; ≠ implementação FE/BE). Design N/A (Tech Lead). AppSec **não** auto-assinado.

Spec: `docs/specs/fase-4/196-orchestrator-playbooks.md` (AC-196-1..7)

## Critérios de aceite

| AC | Status | Evidência |
|---|---|---|
| **AC-196-1** POST `/runs` cria run + persiste steps | **PASS** | `test_ac196_1_create_run_persists_steps` — status ∈ pending/running/awaiting/succeeded; 4 steps recon→exploit |
| **AC-196-2** gate confirmation em semi → `awaiting_confirmation`, sem exploit | **PASS** | `test_ac196_2_confirmation_gate_semi_no_exploit` — exploit sem `engine_run_id`; stub só recon/scan/analyze |
| **AC-196-3** allowlist violada → `scope_violation`, sem avanço silencioso | **PASS** | `test_ac196_3_scope_violation_fails_step` |
| **AC-196-4** cancel → `cancelled` + propaga ao engine stub | **PASS** | `test_ac196_4_cancel_propagates_to_engine` |
| **AC-196-5** GET catálogo lista playbooks MVP | **PASS** | `test_ac196_5_catalog_lists_mvp_playbooks` — web/network/mobile ids |
| **AC-196-6** UI Start + fases (componente) + i18n | **PASS** | Vitest `orchestration-panel.test.tsx` **2/2**; keys `PENTEST$ORCHESTRATION_*` em `translation.json`; `check-translation-completeness` complete |
| **AC-196-7** sem capability exploit → fase não inicia | **PASS** | `test_ac196_7_no_exploit_capability_blocks_phase` — `blocked_capability` / `capability_denied` |

### Deps conhecidas (não bloqueiam)

| Dep | Nota |
|---|---|
| **197** engine stub | Client stub `engine_*` cobre contrato; motor real fora de escopo |
| **198** network | Runner marca `blocked_missing_server` quando mcp-network ausente; i18n `STEP_BLOCKED_SERVER` presente |

## Regressão

| Check | Resultado | Evidência |
|---|---|---|
| EngMgr pytest `tests/test_orchestration.py` | **PASS** (9) | worktree; exit 0 |
| EngMgr pytest suite completa | **PASS** (27) | worktree; exit 0 |
| Vitest `orchestration-panel.test.tsx` | **PASS** (2) | worktree |
| Vitest `no-direct-agent-server-calls` | **PASS** (1) | worktree |
| ESLint escopo orchestration FE | **PASS** | no issues |
| `check-translation-completeness` | **PASS** | complete |
| CI `test-and-build (ubuntu)` | **PASS** | run `31448426795` |
| CI `test-and-build (windows)` | **PASS** | mesmo run |
| mock-LLM E2E (full por `src/hooks/query/**` em `runAllSources`) | **nota** | run `31448426826`: **59 passed / 1 failed / 2 skipped** |

### mock-LLM E2E (nota — não bloqueia AC-196)

- Falha: `settings/mock-llm-profile-management.spec.ts` — `"deletion-guard-inactive" should become active after deleting "deletion-guard-active"` (timeout 15s).
- Diff do tip **não** toca settings UI/API; mesma flake já documentada em PROJETOSIN-192 QA.
- Specs `conversations/*` (mapeadas por `conversation-main.tsx`) **PASS**.
- Tratada como **flake fora do escopo AC-196**; não reabre bloqueio do card.

## Veredicto

**PASS** — AC-196-1..7 verdes com evidência própria (pytest EngMgr + Vitest UI + i18n + CI lint/test/build).  
**Próximo:** Tech Lead despacha **AppSec**. Design N/A. QA não mergeia.
