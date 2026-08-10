---
card: PROJETOSIN-195
pr: 13
veredicto: PASS
agente: appsec
data: 2026-08-10
tip: 1ad19304d
ci: review-manual + PoC AST MCP schemas + confirmation.py + npm-audit-high-clean
repo: klebersjunior/OpenHands
branch: feat/fase3-autonomy-ui-195
---

# AppSecurity — PROJETOSIN-195 (UI modos de autonomia)

**Veredicto:** PASS

Revisor ≠ autor FE (`36344d475` feat; Design/QA docs posteriores). Escopo: UI autonomia + EngMgr PATCH/propagate + regressão fix 187 (schemas MCP / `PENTEST_AUTONOMY_MODE`). Spec `docs/specs/fase-3/195-autonomy-modes-ui.md` § Segurança · ADR-0001 · PR [#13](https://github.com/klebersjunior/OpenHands/pull/13).

Design PASS + QA PASS no tip `1ad19304d` (este laudo). **Não** auto-assina QA/Design.

**Mergeable (eixo AppSec):** sim — todos os gates 195 aplicáveis em PASS para o Tech Lead.

## Checklist

- [x] Sem segredos versionados / hardcoded no diff (session key só via header/`backend.apiKey`; fixtures `test-key`)
- [x] `npm audit --audit-level=high` — sem high/critical (4 moderate pré-existentes: dompurify/monaco/posthog, electron — fora do escopo deste card)
- [x] Session key não bakeada em bundle público (EngMgr client ad-hoc axios com header; não `VITE_*` novo)
- [x] Autonomia runtime **só** via `PENTEST_AUTONOMY_MODE` — HIGH-2 / 187 mantido
- [x] Schemas MCP tools **sem** `autonomy_mode`
- [x] PATCH EngMgr autenticado (`X-Session-API-Key` + capability); não confundir com trust do LLM
- [x] Propagate / `pending_restart` sem vazamento de secrets no wire
- [x] RBAC UI `pentest.autonomy.autonomous`
- [ ] Capability `pentest.autonomy.autonomous` no **server** EngMgr PATCH — **ausente (MEDIUM residual)**
- [ ] `sanitizeMcpToolArguments` wired em call-site de invoke MCP no FE — **ausente (MEDIUM residual)**

## Controles OK (fix 187 / ADR)

### HIGH-2 regressão — schemas MCP + confirmation — **PASS**

**PoC AST** (`mcp-webscan` / `mcp-mobile` / `mcp-recon` `server.py`): nenhum parâmetro `autonomy_mode` nas tools. Ativas só expõem `confirmation_token` onde aplicável.

**`services/mcp-servers/shared/confirmation.py`:**

- `get_autonomy_mode()` lê só `PENTEST_AUTONOMY_MODE`; unknown → fail-closed `semi_autonomous`.
- `require_confirmation(tool_name, payload, *, confirmation_token=…)` — **sem** override de autonomia do caller.
- Docstring explícita: agent/tool args never supply autonomy.

Compose templates EngMgr passam `PENTEST_AUTONOMY_MODE: "{{ autonomy_mode }}"` (web/network/mobile/sast) — source of truth env no runtime, não arg MCP.

### PATCH EngMgr authz — **PASS** (humano + session)

| Controle | Evidência |
|----------|-----------|
| Auth obrigatória | `require_capability("pentest.engagement.create")` → `get_auth_context` → 401 sem/ inválida `X-Session-API-Key` |
| Ownership | `EngagementService.update` → `get(..., user_id=)` — 404 cross-user |
| Body tipado | `EngagementUpdate.autonomy_mode: AutonomyMode \| None` (Literal) |
| FE client | `EngagementService.patchAutonomyMode` envia só `{ autonomy_mode }` + header session; allowlisted axios (não Agent Server tipado) |
| Separação LLM | Hook mid-session PATCH EngMgr + metadata local — **não** patcha settings LLM com autonomy |

Não é o agente MCP: canal CRUD autenticado. Spec § Segurança item 3 cumprido.

### Propagate / `pending_restart` — **PASS** (sem leak)

- `propagate_autonomy_env` reescreve compose via `rewrite_compose` / `_render`.
- Resposta API: só enum `propagation` (`applied` \| `pending_restart` \| `n/a`) em `EngagementOut` — **sem** YAML, paths absolutos de secret, ou `MOBSF_API_KEY`.
- Exceções engolidas → `pending_restart` (sem stack/detail ao client).
- Mobile compose ainda embute `MOBSF_API_KEY` no YAML em disco (pré-existente 191; trust boundary EngMgr + `docker.sock`) — não introduzido no wire deste card.

### RBAC UI autonomous — **PASS**

- `AutonomyModeSelector` / create / chip: `canUseAutonomous` via `useHasPentestCapability("pentest.autonomy.autonomous")`.
- Opção Autônomo sempre visível; `aria-disabled` + tooltip sem capability (AC-195-3 / Design).
- Confirm modal só na elevação → `autonomous`.

Perfil default `pentester` já inclui a capability; analyst/client não têm `engagement.create` (não PATCH).

## Residuals (não bloqueiam)

### MEDIUM — EngMgr não exige `pentest.autonomy.autonomous` no PATCH

PATCH usa só `pentest.engagement.create`. Se no futuro existir perfil com create sem autonomous, API aceitaria `autonomy_mode: autonomous` contornando a UI.

Alinhado a residual documentado em PROJETOSIN-192 (capability server-side deferred). Follow-up: em `patch_engagement` / `update`, se `autonomy_mode == "autonomous"` → `require_capability("pentest.autonomy.autonomous")` (ou 403).

### MEDIUM — `sanitizeMcpToolArguments` sem call-site de produção

Helper + Vitest (AC-195-4, asserção não vácua) existem; **nenhum** invoke MCP no FE chama o sanitize ainda. Controle load-bearing permanece server-side (schema + env). Wire o helper no primeiro path FE que monte tool args.

### LOW — confirmation tokens sticky (187 residual)

`_approved_tokens` / `OPENHANDS_CONFIRMATION_TOKEN` sticky — fora do escopo 195; ainda stub MVP.

## Dependências

```
npm audit --audit-level=high
→ 0 high/critical; 4 moderate (dompurify via monaco/posthog; electron) — pré-existentes, não introduzidos por 195
```

## Evidência PoC (AppSec)

```
webscan/mobile/recon tools: autonomy_mode=False em todas as assinaturas
require_confirmation params: ['tool_name', 'payload', 'confirmation_token']
```

## Ação

1. **PASS** — sem Blocked no Plane.
2. Tech Lead: Design + QA + AppSec PASS neste tip → merge elegível (rebase/`npm test` pós-concorrência se necessário).
3. Residuals MEDIUM → backlog (capability no EngMgr PATCH; wire sanitize quando houver invoke MCP FE).
4. Commit deste laudo na branch do PR (gate artifact).
