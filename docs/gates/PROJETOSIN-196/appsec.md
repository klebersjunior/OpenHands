---
card: PROJETOSIN-196
pr: 16
veredicto: FAIL
agente: appsec
data: 2026-08-11
tip: c18be8706
ci: npm-audit-high-clean; review manual orchestration AuthZ/scope/autonomy
repo: klebersjunior/OpenHands
branch: feat/fase4-orchestrator-196
---

# AppSecurity — PROJETOSIN-196 (Orquestrador + playbooks + UI)

**Veredicto:** FAIL

**Revisor:** AppSec gate (≠ autor do código; ≠ QA). QA permanece em `docs/gates/PROJETOSIN-196/qa.md` (PASS). Design N/A (TL).

## Escopo

Spec `docs/specs/fase-4/196-orchestrator-playbooks.md` § Gates AppSec + foco do card:

1. AuthZ em `/api/pentest/engagements/{id}/orchestration/*`
2. Sem bypass de autonomia / confirmation via body do cliente
3. Playbook id path traversal / injection
4. Scope fail-closed nos steps
5. UI sem secrets; confirmation no canal EngMgr existente
6. Engine stub sem ampliar superfície insegura

Worktree `.tmp/worktrees/196` @ tip `c18be8706` (inclui laudo QA). PR #16.

## Checklist

- [x] Sem segredos versionados / hardcoded no delta (orchestrator / UI / custody)
- [x] `npm audit --audit-level=high` sem high/critical (4 moderate pré-existentes: dompurify/electron — fora do delta 196)
- [x] Rotas com `require_capability` + session (`X-Session-API-Key`); ownership engagement (`created_by`)
- [x] `autonomy_mode` no body ignorado; gate usa `eng.autonomy_mode` server-side (teste `test_autonomy_mode_in_body_ignored`)
- [x] Playbook id: `PLAYBOOK_ID_RE` + stem==id; `../etc/passwd` → 400
- [ ] **Scope fail-closed nos steps** — **FAIL** (ver HIGH abaixo)
- [x] UI: create/advance sem secrets; `POST .../advance` com body `{}`; modal espelha padrão 195
- [x] Engine stub in-process (sem HTTP novo); custody log filtra chaves sensíveis

## Findings

### Critical

Nenhum.

### HIGH — Scope fail-open quando `targets` omitidos; `advance` descarta targets

**Controle pretendido:** `_validate_targets` falha fechado se não há regras de scope, ou se algum target está fora da allowlist (`scope_violation`) — AC-196-3 / foco AppSec #4.

**Quebra:**

1. `_validate_targets` retorna `None` imediatamente quando `targets` é vazio (`runner.py`) — a checagem é **vacuous**.
2. UI (`use-orchestration.ts`) chama `createRun` só com `{ playbook_id }` — **nunca envia targets**. O caminho de produção do painel inicia fases `engine_start_phase` **sem** validar allowlist.
3. `OrchestrationRun` **não persiste** `targets`. `advance()` (router sem body) chama `_execute_from(..., targets=[])`. Mesmo um `POST /runs` API com targets válidos perde o conjunto no advance: fases pós-confirmação (incl. `exploit`) revalidam com lista vazia → scope skip + `engine.start_phase(..., targets=None)`.

**Impacto:** o gate de scope deixa de ser load-bearing no fluxo UI e no caminho pós-confirmation. Com motores reais (197+), fases ofensivas podem ser despachadas sem allowlist revalidada. Stub atual não amplia impacto de rede, mas o controle do orquestrador já está incorreto.

**Remediação mínima (bloqueia merge AppSec):**

- Persistir `targets` no run (coluna JSON ou equivalente).
- Antes de qualquer `engine.start_phase`: exigir targets não vazios **ou** derivar do engagement e validar cada um; sem targets resolvíveis → `scope_violation` / `targets_required` (fail-closed).
- `advance()` deve reutilizar targets persistidos (não `[]`).
- Testes: omit targets → fail-closed; create com targets + advance → mesmos targets revalidados; UI passa targets (engagement scope / seleção) ou o servidor deriva.

### MEDIUM — Capability Start só no servidor (UI sem gate)

Rotas mutáveis exigem `pentest.scan.passive` (403 para profile `client` — `test_view_only_cannot_start_run`). O painel não esconde Start/Cancel/Advance via `useHasPentestCapability`. Alinhado a residuais 192 (session + server AuthZ). Não eleva a FAIL sozinho.

### LOW — Campo `autonomy_mode` aceito no schema CreateRunRequest

Documentado como ignorado; teste cobre não-bypass. Preferível `model_config` extra forbid ou omitir o campo para reduzir superfície confusa — cosmético.

### LOW — Catálogo GET mescla playbooks do stub engine que `get_playbook` (local-only) não inicia

UI pode listar ids engine-only; create retorna 400. Sem bypass de execução; inconsistência UX.

## Controles verificados (OK)

| Controle | Evidência |
|---|---|
| Session + capability nas rotas | `orchestration.py` + `shared/auth_middleware.require_capability` |
| Ownership engagement | `_get_engagement` 404 se `created_by != user_id` |
| Autonomia server-side | `eng.autonomy_mode`; body ignorado; teste dedicado |
| Confirmation channel | `POST .../advance` autenticado; UI modal → `advanceRun` sem payload de autonomia |
| Exploit capability | `_phase_requires_exploit_cap` → `blocked_capability` (AC-196-7) |
| Playbook id sanitization | `PLAYBOOK_ID_RE`, stem==id, teste traversal |
| Engine stub superfície | In-process singleton; sem bind/HTTP novo no 196 |
| Custody sem secrets | `custody.py` filtra api_key/token/password/secret/prompt/session_api_key |
| FE ad-hoc HTTP allowlist | `orchestration-service.ts` em `no-direct-agent-server-calls.test.ts` |
| npm audit high+ | 0 high/critical |

## Dependências

`npm audit --audit-level=high`: **PASS** (0 high/critical). Moderates pré-existentes (dompurify via monaco/posthog; electron) — fora do delta 196.

## Ação requerida

1. **Backend** remedia HIGH (persist targets + fail-closed + advance reusa targets + testes).
2. Re-despachar **AppSec** após tip corrigido (revisor ≠ autor).
3. Label Plane **Blocked** enquanto FAIL.
4. **Não mergear.**

**Não mergeado por AppSec.** Tech Lead: veredicto **FAIL**, finding HIGH scope fail-open, PR https://github.com/klebersjunior/OpenHands/pull/16, laudo este arquivo.
