---
card: PROJETOSIN-196
pr: 16
veredicto: PASS
agente: qa
data: 2026-08-10
repo: klebersjunior/OpenHands
branch: feat/fase4-orchestrator-196
commit: d15d3f5e4
prev_qa: 51661f67f / c18be8706
appsec_fix: 113258fca
appsec_laudo: d15d3f5e4 (PASS — não reassinado por QA)
ci: pr-title SUCCESS @ tip; lint/test/build re-check pós-push laudo
design: N/A (TL — UI chips/botões)
---

# QA Report — PROJETOSIN-196 Orquestrador + playbooks + UI (re-QA)

**Veredicto:** PASS  
**PR:** https://github.com/klebersjunior/OpenHands/pull/16  
**Tip avaliado:** `d15d3f5e4c8502601fc41339605c2ac58e1e2678`  
**Inclui remediação AppSec:** `113258fca` (fail-closed targets) + laudo `docs/gates/PROJETOSIN-196/appsec.md`  
**Worktree:** `.tmp/worktrees/196`  
**Revisor:** QA Agent (evidência própria; ≠ implementação FE/BE; ≠ AppSec). Design N/A (Tech Lead). **AppSec não reassinado** neste re-QA.

Spec: `docs/specs/fase-4/196-orchestrator-playbooks.md` (AC-196-1..7)

## Motivo do re-QA

Tip avançou após AppSec FAIL → remediação HIGH (scope fail-open em targets vazios) → AppSec PASS. Laudo QA anterior (`51661f67f` / `c18be8706`) ficou atrás do tip; revalidação obrigatória sem auto-assinar AppSec.

## Critérios de aceite

| AC | Status | Evidência |
|---|---|---|
| **AC-196-1** POST `/runs` cria run + persiste steps | **PASS** | `test_ac196_1_create_run_persists_steps` |
| **AC-196-2** gate confirmation em semi → `awaiting_confirmation`, sem exploit | **PASS** | `test_ac196_2_confirmation_gate_semi_no_exploit` |
| **AC-196-3** allowlist violada → `scope_violation`, sem avanço silencioso | **PASS** | `test_ac196_3_scope_violation_fails_step` |
| **AC-196-4** cancel → `cancelled` + propaga ao engine stub | **PASS** | `test_ac196_4_cancel_propagates_to_engine` |
| **AC-196-5** GET catálogo lista playbooks MVP | **PASS** | `test_ac196_5_catalog_lists_mvp_playbooks` |
| **AC-196-6** UI Start + fases (componente) + i18n | **PASS** | Vitest `orchestration-panel.test.tsx` **2/2** (ainda verde pós-`targets` no tipo) |
| **AC-196-7** sem capability exploit → fase não inicia | **PASS** | `test_ac196_7_no_exploit_capability_blocks_phase` |

### Regressões pós-remediação AppSec (targets / hidratação / advance)

| Teste | Status |
|---|---|
| `test_empty_targets_without_scope_fail_closed` | **PASS** |
| `test_empty_targets_hydrates_from_scope_allowlist` | **PASS** |
| `test_advance_reuses_persisted_targets` | **PASS** |
| `test_advance_without_persisted_targets_fail_closed` | **PASS** |

### Deps conhecidas (não bloqueiam)

| Dep | Nota |
|---|---|
| **197** engine stub | Client stub `engine_*` cobre contrato; motor real fora de escopo |
| **198** network | Runner marca `blocked_missing_server` quando mcp-network ausente |

## Regressão

| Check | Resultado | Evidência |
|---|---|---|
| EngMgr pytest `tests/test_orchestration.py` | **PASS** (13) | worktree @ `d15d3f5e4`; exit 0 |
| EngMgr pytest suite completa | **PASS** (31) | worktree; exit 0 |
| Vitest `orchestration-panel.test.tsx` | **PASS** (2) | worktree |
| AppSec laudo | **PASS** (externo) | `docs/gates/PROJETOSIN-196/appsec.md` — QA **não** reassinou |

## Veredicto

**PASS** — AC-196-1..7 + regressões de targets/hidratação/advance verdes no tip pós-remediação.  
**Próximo:** Tech Lead (merge policy). QA não mergeia. AppSec permanece PASS no laudo próprio (não reassinado).
