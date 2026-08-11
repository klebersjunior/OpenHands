---
card: PROJETOSIN-199
pr: 18
veredicto: PASS
agente: appsec
data: 2026-08-10
tip: 1b5a51a61
ci: npm-audit-high-clean; review manual OTEL redaction + custody AuthZ
repo: klebersjunior/OpenHands
branch: feat/fase4-observability-199
---

# AppSecurity — PROJETOSIN-199 (SigNoz OTEL + chain of custody)

**Veredicto:** PASS

**Revisor:** AppSec gate (papel ≠ autor da implementação; não assina QA/Design). Review formal no PR #18.

## Escopo

Spec `docs/specs/fase-4/199-observability-signoz-custody.md` — eixos obrigatórios do gate:

1. Redaction (session keys, Authorization, tokens GVM/MSF, passwords) em spans/logs/custody
2. `PENTEST_OTEL_LLM_BODIES` default false; sem corpos de prompt/resposta por default
3. OTEL headers/secrets só via env — nada no git
4. Custody AuthZ: GET com capability; POST `/internal/custody` com session key; metadata redacted na hash chain
5. Sem provisionar SigNoz com credenciais; PostHog product analytics intacto
6. Exporter no-op sem endpoint (sem outbound acidental em CI)

Worktree `.tmp/worktrees/199` @ tip `1b5a51a61`. PR #18.

## Checklist

- [x] Sem segredos versionados / hardcoded (OTEL headers vazios em `.env.sample` / `defaults.json`)
- [x] `npm audit --audit-level=high` sem high/critical (4 moderate pré-existentes: dompurify/electron — fora do delta 199)
- [x] Redaction canônica em `services/shared/redaction.py` cobre Authorization, session/API keys, password/passwd/secret/token/cookie, `msf_*pass` / `gvm_*pass`, bearer inline / `sk-` / `ghp_` / Slack tokens; usada em `otel_setup.start_span` e custody hash/persist
- [x] `PENTEST_OTEL_LLM_BODIES` documentado default `false` (`.env.sample`, `defaults.json` → `llmBodies: false`); `llm_bodies_enabled()` só retorna true com env truthy; **nenhum call site emite corpo LLM** neste PR
- [x] OTLP headers lidos só de `OTEL_EXPORTER_OTLP_HEADERS` em runtime; sample comentado sem valor; teste AC-199-6 rejeita assignment não-vazio
- [x] GET `.../custody` → `require_capability("pentest.findings.view")`; POST `/internal/custody` → `require_authenticated()` (session key); metadata scrubbed antes de persist/hash
- [x] Sem compose/imagem SigNoz neste PR; `defaults.json` comenta namespace separado de PostHog; `src/services/telemetry.ts` **não tocado**
- [x] Sem `OTEL_EXPORTER_OTLP_ENDPOINT` → `otel_enabled()` false → sem `OTLPSpanExporter` (AC-199-1)

## Findings

### Critical / High

Nenhum. **Sem bloqueio.**

### MEDIUM — Redaction duplicada/fraca em `mcp-servers/shared/otel_tool_span.py`

O helper MCP reimplementa scrub só por nome de chave (regex menor; sem `msf`/`gvm`/`set-cookie`; **sem** `redact_string` em valores). Spans de tool que passem attrs com segredo sob chave “inofensiva” ou bearer inline em string podem vazar.

**Mitigação atual:** decorator `with_mcp_tool_span` só anexa `tool` + `engagement.id` (superfície estreita neste PR). Path canônico EngMgr/Findings usa `shared.redaction`.

**Decisão:** residual MEDIUM — não FAIL. Follow-up: reutilizar `services/shared/redaction.py` (ou extrair pacote comum) no helper MCP.

### MEDIUM — GET custody sem ownership de engagement

Qualquer sessão com `pentest.findings.view` lista a chain de **qualquer** `engagement_id` (UUID). Spec exige só a capability; membership EngMgr ainda não é load-bearing (paridade Findings ownership documentada no serviço).

**Decisão:** residual MEDIUM — aceitável no modelo single-key local; reforçar quando RBAC multi-tenant/EngMgr membership existir.

### MEDIUM — POST `/internal/custody` append cross-engagement com qualquer session válida

Alinhado à spec (API interna + session key). Sem capability extra nem allowlist de caller. Poisoning da chain exige chave válida + reachability de rede ao Findings.

**Decisão:** residual MEDIUM — manter endpoint fora de exposição pública (rede/compose); opcionalmente restringir a service identity futura.

### LOW — `actor` = prefixo da session key (`session:{key[:8]}`)

`AuthContext.user_id` (pré-existente) vira `actor` em custody e é listável. Expõe 8 chars do material da chave na trilha de auditoria.

**Decisão:** residual LOW — padrão já usado em Findings `created_by`; preferir actor opaco/estável em follow-up de AuthZ.

### LOW — Sem teste dedicado 401/403 nos endpoints custody

Auth compartilhado já coberto em `test_findings_crud` (401/403). Custody confia no mesmo middleware.

### LOW — Asserção vacua em `test_otel_config_docs.py`

Trecho com `or True` torna uma checagem de `signoz-ingestion-key=` sempre verdadeira; a checagem forte de linhas `OTEL_EXPORTER_OTLP_HEADERS=` não-vazias permanece.

## Controles verificados

| Controle | Evidência |
|---|---|
| Redaction spans | `otel_setup.start_span` → `redact_mapping` |
| Redaction custody | `build_custody_event` / `CustodyService.append`; teste API assert `Authorization` → `[REDACTED]` |
| LLM bodies off | `llmBodies: false`; env default `"false"`; sem emitters de prompt/response |
| Secrets OTEL | `.env.sample` comentado; `exporterOtlpHeaders: ""`; sem compose SigNoz |
| AuthZ GET | `require_capability("pentest.findings.view")` |
| AuthZ POST internal | `require_authenticated()` |
| No-op CI | `setup_otel` só instancia exporter se `otel_enabled() and otlp_endpoint()` |
| PostHog isolado | sem diff em `src/services/telemetry.ts`; comentário em `defaults.json` |

## Dependências

`npm audit --audit-level=high`: **PASS** (0 high/critical). Moderates pré-existentes (dompurify via monaco/posthog; electron) — fora do delta 199.

## Ação requerida

Nenhuma para merge AppSec. Residuais MEDIUM → backlog (unificar redaction MCP; ownership custody; endurecer `/internal`).

**Não mergeado por AppSec.** Tech Lead decide merge com QA+AppSec PASS (Design N/A).
