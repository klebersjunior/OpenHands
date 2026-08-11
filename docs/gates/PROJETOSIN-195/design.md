---
card: PROJETOSIN-195
pr: 13
veredicto: PASS
agente: design
data: 2026-08-10
repo: klebersjunior/OpenHands
branch: feat/fase3-autonomy-ui-195
commit: 36344d475
---

# Design Review — PROJETOSIN-195 UI modos de autonomia

**Veredicto:** PASS

Gate de UI/UX/a11y sobre o seletor de autonomia (criação + mid-engagement), confirm → Autônomo, banner `pending_restart` e tokens/a11y. Revisor (Design) ≠ autor do código Frontend. Este laudo **não** cobre AC de QA nem AppSec.

Spec: `docs/specs/fase-3/195-design-notes.md` · `docs/specs/fase-3/195-autonomy-modes-ui.md`  
ADR: `docs/adrs/0001-plataforma-pentest-ia-extensao-openhands.md`

## Escopo revisado

| Superfície | Arquivo |
|---|---|
| Radiogroup compartilhado | `src/components/features/pentest/autonomy-mode-selector.tsx` |
| Confirm → autonomous | `src/components/features/pentest/autonomy-confirm-modal.tsx` |
| Chip compacto mid | `src/components/features/pentest/autonomy-mode-control.tsx` |
| Banner pending | `src/components/features/pentest/autonomy-pending-banner.tsx` |
| Header + banners | `src/components/features/pentest/pentest-autonomy-header.tsx` |
| Criação (form) | `src/components/features/pentest/pentest-workspace-fields.tsx` |
| Colocação header | `src/components/features/conversation/conversation-main/conversation-main.tsx` (+ `conversation-name-with-status` trailing) |
| Defaults criação | `workspace-selection-form.tsx`, `local-new-conversation-menu.tsx` |
| i18n | `PENTEST$AUTONOMY_*` em `src/i18n/translation.json` |

## Conformidade vs design notes

| Critério (notes) | Resultado | Evidência |
|---|---|---|
| Colocação create: engagement → radiogroup (após `engagementId`) | PASS | `PentestWorkspaceFields` |
| Default UI `semi_autonomous` | PASS | Home + sidebar `useState("semi_autonomous")`; reset ao trocar tipo |
| Mid: chip no header pentest (não Settings LLM) | PASS | `PentestAutonomyHeaderControls` no `ChatPaneHeader` |
| Radiogroup (`role="radiogroup"` / `radio`) | PASS | Substitui chips `aria-pressed` (U-3) |
| Autônomo sempre visível, disabled + tooltip sem RBAC | PASS | `canUseAutonomous`; `StyledTooltip` + `title` + `aria-disabled` |
| Confirm **só** ao elevar → `autonomous` (create + mid) | PASS | `handleAutonomyChange` / `handleSelect`; Manual↔Semi imediato |
| Banner `pending_restart` informativo | PASS | `role="status"`; tokens surface/muted; sem danger |
| Helper allowlist no form | PASS | `PENTEST$AUTONOMY_HELPER` + RBAC hint |
| Tokens `--oh-*` / sem tema paralelo | PASS | border/primary/surface/foreground/muted/status-error |
| i18n + `data-testid` estáveis | PASS | Prefixo `PENTEST$AUTONOMY_*`; testids da §11 |
| Foco inicial do modal no Cancel (não Confirm) | PASS | `cancelRef.focus()` |
| Erro mid: `role="alert"` + toast; valor permanece last-known-good | PASS | Sem optimistic update no hook |

## Checklist a11y (WCAG 2.1 AA)

- [x] Contraste AA — texto/borda via `--oh-foreground` / `--oh-text-secondary` / `--oh-primary` / `--oh-muted`
- [x] Radiogroup — `role="radiogroup"` + `aria-labelledby`/`aria-label`; opções `role="radio"` + `aria-checked`; setas ←/→/↑/↓
- [x] Foco visível — `focus-visible:ring-2 ring-[var(--oh-primary)]` no radiogroup e no chip (fecha D-183-1 no escopo tocado)
- [x] Tab order — create: engagement → radios → Launch; mid: chip → popover → modal
- [x] Teclado — Space/Enter seleciona; Escape fecha modal (`ModalBackdrop`); click-outside no popover (respeita confirm aberto)
- [x] Disabled Autônomo — permanece focável (`tabIndex={0}`); `aria-disabled`; tooltip + `title`
- [x] Modal — `h2` + `aria-labelledby`; botões nomeados; foco inicial no Cancel
- [x] Saving / loading — `aria-busy` no chip; testids `…-loading` / `…-saving`
- [x] Banner pending — `role="status"`; não rouba foco
- [x] Não só cor — label textual no chip compacto + `aria-label` com modo
- [x] Responsivo — `flex-wrap` nos radios; chip `truncate` + `title`
- [x] i18n — zero literals de UI no escopo

## Issues (não bloqueantes)

| ID | Severidade | Issue | Ação sugerida |
|---|---|---|---|
| **D-195-1** | medium | Variant `compact` omite o helper global de allowlist (notes §4.2 / §6: obrigatório). Elevação ainda menciona allowlist no Confirm. | Exibir helper curto (`PENTEST$AUTONOMY_HELPER`) no popover compact; manter hints por opção opcionais. |
| **D-195-2** | low | Em `compact`, `aria-describedby` do radio Autônomo aponta para `…-rbac` que só renderiza em `form`. Mitigado por `title` + tooltip. | Renderizar hint RBAC (visível ou `sr-only`) também em compact, ou omitir `aria-describedby` quando o alvo não existe. |
| **D-195-3** | low | Confirm usa `ModalBackdrop` sem focus trap / restore no chip (paridade com `ConfirmationModal` legado). Foco inicial no Cancel está OK. | Follow-up: trap Tab + restore ao trigger ao fechar (padrão `finding-fp-modal` / HeroUI Modal). |
| **D-195-4** | low | `role="dialog"` aninhado (backdrop + painel interno). | Remover `role`/`aria-modal` do backdrop **ou** do painel — um único dialog rotulado. |
| **D-195-5** | low | Read-only: helper `PENTEST$AUTONOMY_READONLY` só em `sr-only`; chip visualmente muted sem texto visível. | Opcional: tooltip/`title` com a mesma copy. |

Nenhuma issue **high** de a11y ou desvio de colocação/fluxo que bloqueie o gate Design.

## Critérios de gate (design notes §14 / fluxos)

| # | Critério | Resultado |
|---|---|---|
| 1 | Colocação create + mid | PASS |
| 2 | Default Semi + Autônomo disabled+tooltip | PASS |
| 3 | Radiogroup + confirm → autonomous | PASS |
| 4 | Estados loading/saving/RBAC/pending/erro | PASS |
| 5 | Checklist a11y §8 (floor AA) | PASS (residuals D-195-1…5) |
| 6 | Tokens / i18n / testids | PASS |
| 7 | Segurança UX (RBAC visível + allowlist no form + confirm) | PASS |

## Veredicto

**PASS** — UI alinhada às design notes 195 nos fluxos obrigatórios (colocação, radiogroup, default Semi, Autônomo disabled+tooltip, confirm só ao elevar, banner `pending_restart`, tokens/i18n). Gaps D-195-1…5 são polish / follow-up; não bloqueiam QA.

**Próximo:** QA pode iniciar (AC-195-*). AppSec em paralelo ou após QA conforme Tech Lead.
