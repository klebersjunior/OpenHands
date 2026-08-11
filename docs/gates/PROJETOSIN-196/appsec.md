---
card: PROJETOSIN-196
pr: 16
veredicto: PASS
agente: appsec
data: 2026-08-11
tip: 113258fca
ci: npm-audit-high-clean; pytest test_orchestration (13 passed); re-gate pós-remediação HIGH targets
repo: klebersjunior/OpenHands
branch: feat/fase4-orchestrator-196
prev_fail: afcd8db5a (laudo FAIL @ c18be8706)
fix_author: Kleber Aquino (≠ revisor AppSec)
---

# AppSecurity — PROJETOSIN-196 (Orquestrador + playbooks + UI) — re-gate

**Veredicto:** PASS

**Revisor:** AppSec gate (≠ autor do fix `113258fca`; ≠ QA). QA permanece em `docs/gates/PROJETOSIN-196/qa.md` (PASS). Design N/A (TL).

## Escopo

Re-gate após remediação do HIGH de scope fail-open. Spec `docs/specs/fase-4/196-orchestrator-playbooks.md` § Gates AppSec + foco do card. Worktree `.tmp/worktrees/196` @ tip `113258fca`. PR #16.

## Checklist

- [x] Sem segredos versionados / hardcoded no delta (orchestrator / UI / custody)
- [x] `npm audit --audit-level=high` sem high/critical (4 moderate pré-existentes: dompurify/electron — fora do delta 196)
- [x] Rotas com `require_capability` + session (`X-Session-API-Key`); ownership engagement (`created_by`)
- [x] `autonomy_mode` no body ignorado; gate usa `eng.autonomy_mode` server-side
- [x] Playbook id: `PLAYBOOK_ID_RE` + stem==id; traversal → 400
- [x] **Scope fail-closed nos steps** — fechado pelo fix `113258fca` (ver abaixo)
- [x] UI: create/advance sem secrets; `POST .../advance` com body `{}`; modal espelha padrão 195
- [x] Engine stub in-process (sem HTTP novo); custody log filtra chaves sensíveis

## Fechamento do HIGH (reprovado no FAIL anterior)

| Critério de remediação | Evidência @ `113258fca` |
|---|---|
| Start sem targets: hidrata do engagement allow **ou** 400 `targets_required` | `_resolve_targets` + `create_run` → 400 se vazio; testes `test_empty_targets_*` |
| Nunca skip allowlist com lista vazia | `_validate_targets`: empty → erro; `start_phase` só após validação |
| Targets persistidos no run | coluna JSON `OrchestrationRun.targets` + migração `003_orchestration_run_targets.py` |
| `advance()` revalida o mesmo conjunto (sem override cliente) | router sem body de targets; `advance()` lê `run.targets` apenas; teste `test_advance_reuses_persisted_targets` |
| PoC FAIL (UI só `playbook_id`) não bypassa scope | FE ainda omite targets; servidor hidrata allowlist ou 400; `test_empty_targets_hydrates_from_scope_allowlist` / `test_empty_targets_without_scope_fail_closed` |

**Verificação local:** `uv run --extra dev pytest tests/test_orchestration.py` → **13 passed** (incl. 4 regressões de targets).

## Findings

### Critical / HIGH

Nenhum aberto.

### MEDIUM — Capability Start só no servidor (UI sem gate)

Rotas mutáveis exigem `pentest.scan.passive` (403 para profile `client`). O painel não esconde Start/Cancel/Advance via `useHasPentestCapability`. Alinhado a residuais 192 (session + server AuthZ). **Não bloqueia.**

### LOW — Campo `autonomy_mode` aceito no schema CreateRunRequest

Documentado como ignorado; teste cobre não-bypass. Preferível omitir / `extra=forbid` — cosmético.

### LOW — Catálogo GET mescla playbooks do stub engine que `get_playbook` (local-only) não inicia

UI pode listar ids engine-only; create retorna 400. Sem bypass de execução.

## Controles verificados (OK)

| Controle | Evidência |
|---|---|
| Session + capability nas rotas | `orchestration.py` + `require_capability` |
| Ownership engagement | `_get_engagement` 404 se `created_by != user_id` |
| Autonomia server-side | `eng.autonomy_mode`; body ignorado |
| Confirmation channel | `POST .../advance` autenticado; sem payload de autonomia/targets |
| Scope fail-closed + persistência | `runner.py` `_resolve_targets` / `_validate_targets` / `run.targets` |
| Exploit capability | `_phase_requires_exploit_cap` → `blocked_capability` |
| Playbook id sanitization | `PLAYBOOK_ID_RE`, stem==id |
| Engine stub superfície | In-process singleton; sem bind/HTTP novo |
| Custody sem secrets | filtro api_key/token/password/secret/… |
| npm audit high+ | 0 high/critical |

## Dependências

`npm audit --audit-level=high`: **PASS** (0 high/critical). Moderates pré-existentes (dompurify via monaco/posthog; electron) — fora do delta 196.

## Ação requerida

1. Label Plane **Blocked** — **remover** (este PASS).
2. Tech Lead: demais gates / merge policy; **AppSec não mergeia**.
3. Residuais MEDIUM/LOW acima — não bloqueiam merge AppSec.

**Não mergeado por AppSec.** Tech Lead: veredicto **PASS**, HIGH de targets fechado, PR https://github.com/klebersjunior/OpenHands/pull/16, tip `113258fca`, laudo este arquivo.
