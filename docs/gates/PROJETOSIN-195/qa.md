---
card: PROJETOSIN-195
pr: 13
veredicto: PASS
agente: qa
data: 2026-08-10
repo: klebersjunior/OpenHands
branch: feat/fase3-autonomy-ui-195
commit: 20a574a34794b6a5d26cf6cb29c26a9cf9d35898
ci: vitest-scoped+i18n+engmgr-pytest; e2e-mock-llm N/A (fora mapping)
---

# QA Report — PROJETOSIN-195 UI modos de autonomia

**Veredicto:** PASS  
**PR:** https://github.com/klebersjunior/OpenHands/pull/13  
**Tip avaliado:** `20a574a34794b6a5d26cf6cb29c26a9cf9d35898` (FE + Design; laudo QA neste PR)  
**Worktree:** `.tmp/worktrees/195`  
**Revisor:** QA ≠ autor FE. Design PASS **não** auto-assina AC. Evidência própria.

Spec: `docs/specs/fase-3/195-autonomy-modes-ui.md`  
Design: `docs/gates/PROJETOSIN-195/design.md` (PASS)

## Critérios de aceite

| AC | Status | Evidência |
|---|---|---|
| **AC-195-1** Default UI = Semi (`semi_autonomous`) | **PASS** | `workspace-selection-form.tsx` / `local-new-conversation-menu.tsx` init `useState("semi_autonomous")`; Vitest `AutonomyModeSelector` + `PentestWorkspaceFields` → `aria-checked=true` em `pentest-autonomy-semi_autonomous` |
| **AC-195-2** Manual → PATCH EngMgr → GET `manual` | **PASS** | FE: `engagement-service.test.ts` PATCH body `{ autonomy_mode: "manual" }` + resposta; EngMgr: `test_patch_autonomy_returns_propagation_n_a` PATCH→GET `manual` (**1 passed**) |
| **AC-195-3** Sem capability → Autônomo não selecionável | **PASS** | Vitest: opção visível, `aria-disabled`/`data-disabled`, click **não** chama `onChange` |
| **AC-195-4** Client não envia `autonomy_mode` em MCP tool args | **PASS** | `sanitizeMcpToolArguments` + Vitest strip/detect; **vacuidade:** identity `return args` → teste **FAIL** (`expected … autonomy_mode`); restaurado; FE `autonomy_mode` só em EngMgr CRUD / metadata (não tool MCP) |
| **AC-195-5** Banner `pending_restart` (propagation ≠ applied) | **PASS** | Mock EngMgr PATCH `propagation: "pending_restart"`; `AutonomyPendingBanner` testid; wiring `conversation-main` → `pendingRestart={propagation === "pending_restart"}` → `PentestAutonomyBanners` |
| **AC-195-6** i18n keys completas | **PASS** | 21× `PENTEST$AUTONOMY_*` × 15 idiomas; `declaration.ts` enum; `npm run check-translation-completeness` → complete |

## Regressão

| Check | Resultado | Evidência |
|---|---|---|
| Vitest escopo AC | **PASS** 9/9 | `engagement-service.test.ts` + `autonomy-mode-selector.test.tsx` + `no-direct-agent-server-calls.test.ts` |
| EngMgr pytest PATCH→GET | **PASS** 1/1 | `test_patch_autonomy_returns_propagation_n_a` |
| `check-translation-completeness` | **PASS** | All keys complete |
| eslint escopo autonomy/engagement | **PASS** | sem issues nos paths tocados |
| E2E mock-LLM | **N/A** | `test-mapping.json` sem mapping pentest/autonomy; fora escopo deste gate |

## Segurança regressão (foco QA, não AppSec)

- Controle FE: `src/api/pentest/mcp-tool-payload.ts` — strip de `autonomy_mode` antes de qualquer invoke MCP.
- Asserção **não vácua**: sem o strip, Vitest AC-195-4 falha.
- **Residual para AppSec:** helper ainda sem call-site de invoke MCP no FE (não há path que monte tool args com autonomy); AppSec deve confirmar schemas MCP sem `autonomy_mode` + authz PATCH EngMgr + RBAC autonomous.

## Veredicto

**PASS** — AC-195-1…6 com evidência própria; Design PASS mantido.  
**AppSec pode iniciar.** QA não mergeia; não emite AppSec.
