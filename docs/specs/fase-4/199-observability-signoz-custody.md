# Spec Técnica — PROJETOSIN-199: Observabilidade SigNoz + chain of custody

**ADR:** docs/adrs/0001-plataforma-pentest-ia-extensao-openhands.md (accepted) — blueprint §10  
**Card Plane:** PROJETOSIN-199 — `e307cc54-a24f-4317-a6b7-d489fa5ea3ac`  
**Agentes:** devops (lead) + backend (instrumentação serviços)  
**Prioridade:** P1 — paralelo a 197 (baixo acoplamento)  
**Base git:** `e32b31018`  
**Branch:** `feat/fase4-observability-199`  
**Worktree:** `.tmp/worktrees/199`  
**PR target:** fork `klebersjunior/OpenHands` only

---

## Objetivo

Entregar pipeline de **observabilidade por engagement**: logs/traces estruturados (comandos runtime, outputs resumidos, decisões LLM **redacted**, mudanças de finding) exportáveis para **SigNoz** já operado na Heimdall, mais trilha de **chain of custody** auditável (append-only / hash chain leve) referenciando evidências no storage do engagement.

Não depende de 197/198 para o MVP de telemetria dos serviços já existentes (EngMgr, Findings, MCP shared).

---

## Premissas

1. SigNoz Heimdall já existe — **não** provisionar stack SigNoz nova no compose do engagement por default; apenas **export OTLP** configurável.
2. Telemetria Canvas PostHog (`src/services/telemetry.ts`) **permanece** para analytics de produto; este card é **ops/security audit** (OTEL → SigNoz), namespaces separados.
3. **Zero secrets** em spans/logs: redaction obrigatória (API keys, `Authorization`, `X-Session-API-Key`, passwords, tokens MSF/GVM, cookies).
4. Prompts/respostas LLM: só **resumo** (hash + length + model id); nunca corpo completo por default (`PENTEST_OTEL_LLM_BODIES=false`).
5. Autonomia/escopo: emitir evento quando `scope_violation` / `confirmation_required` ocorrer (anomalia).
6. Não usar MCP SigNoz de sessão interativa no código de runtime — só OTLP exporter standard.

---

## Contrato de telemetria

### Resource attributes (obrigatórios)

| Attr | Exemplo |
|---|---|
| `service.name` | `engagement-manager` / `findings-service` / `mcp-recon` / … |
| `engagement.id` | UUID |
| `deployment.mode` | `electron` \| `server` \| `dev` |

### Span / log event names (canônicos)

| Name | Quando |
|---|---|
| `pentest.mcp.tool` | Início/fim tool MCP (attrs: `tool`, `ok`, `error_code?`) |
| `pentest.runtime.command` | Comando allowlisted no runtime (argv resumido) |
| `pentest.finding.mutate` | Create/update/triage FP |
| `pentest.scope.violation` | Tentativa fora allowlist |
| `pentest.confirmation.gate` | Pedido/aprovação (ids, sem payload sensível) |
| `pentest.engine.run` | Se 197 já emitiu — consumir mesmo schema |
| `pentest.custody.append` | Novo elo chain-of-custody |

### Trace context

- Propagar `traceparent` onde houver HTTP interno (EngMgr ↔ Findings ↔ futuros).
- MCP stdio: gerar root span por invocação de tool com `engagement.id` no resource.

---

## Chain of custody

Módulo compartilhado (Python) em `services/shared/custody.py` (ou `services/mcp-servers/shared/custody.py` se só MCP — **preferir `services/shared/`** para EngMgr/Findings também):

```text
CustodyEvent {
  id, ts, engagement_id, actor, action, resource_type, resource_id,
  prev_hash, hash, metadata_redacted
}
```

- `hash = SHA-256(prev_hash || canonical_json(event_without_hash))`
- Persistência MVP: tabela Postgres no Findings Service **ou** arquivo append-only no volume do engagement (`custody.jsonl`) — **escolha:** tabela `custody_events` no Findings Service (já tem Postgres) + API interna `POST /internal/custody` autenticada por session key.
- API de leitura: `GET /api/engagements/{id}/custody` (ou sob Findings) com capability `pentest.findings.view` / admin.
- Evidências: metadata só **refs** (`s3://…` / path relativo bucket engagement), não bytes.

---

## Layout

```
services/shared/
  otel_setup.py          # init TracerProvider + LoggerProvider + OTLP
  redaction.py           # scrub secrets
  custody.py             # hash chain helpers
services/findings-service/
  app/models/custody.py
  app/routers/custody.py
  alembic/versions/*_custody_events.py
  tests/test_custody_chain.py
services/engagement-manager/
  # wiring otel_setup no lifespan
services/mcp-servers/shared/
  otel_tool_span.py      # decorator/context para tools
docker/ / docs/
  # nota: OTEL_EXPORTER_OTLP_ENDPOINT apontando ao collector SigNoz
config/defaults.json     # pentest.otel.* defaults (endpoint vazio = no-op)
.env.sample              # OTEL_* vars documentadas
docs/gates/PROJETOSIN-199/  # preenchido por gates, não por este PR necessariamente
```

Exporter **no-op** quando endpoint vazio — CI sem SigNoz.

---

## Env

| Variable | Purpose |
|----------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Collector SigNoz (ex. `https://…:4318`) |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth collector se necessário (secret env) |
| `OTEL_SERVICE_NAME` | Override pontual |
| `PENTEST_OTEL_ENABLED` | default `true` se endpoint set; else false |
| `PENTEST_OTEL_LLM_BODIES` | default `false` |
| `ENGAGEMENT_ID` | resource attr |

---

## AC testáveis

| ID | Critério |
|---|---|
| AC-199-1 | Sem endpoint OTLP: app sobe; exporter no-op; testes passam |
| AC-199-2 | Redaction remove session key / Authorization de atributos de log |
| AC-199-3 | Custody append: hash chain quebra se evento do meio for alterado (teste unitário) |
| AC-199-4 | `scope_violation` gera evento/log com nome canônico |
| AC-199-5 | Finding create dispara `pentest.finding.mutate` (span ou log) — assert via span exporter in-memory nos testes |
| AC-199-6 | `.env.sample` + `defaults.json` documentam vars; sem secrets commitados |

---

## Gates

| Gate | Foco |
|---|---|
| AppSec | Leak de secrets em telemetria; custody tamper-evidence; AuthZ leitura custody |
| QA | AC-199-* |
| Design | N/A (dashboards SigNoz fora do Canvas; opcional doc de queries) |

---

## Fora de escopo

- UI Canvas de “timeline custody” rica (pode ser Fase 5) — API + export bastam
- Provisionar SigNoz/ClickHouse no monorepo
- Substituir PostHog product analytics
- Alertas SigNoz complexos (doc de exemplo OK)

---

## Entrega

1. Worktree 199 · PR fork `Plane: PROJETOSIN-199`  
2. Comentário Plane + notas de config SigNoz (endpoint) **sem** credenciais  
3. Gates QA + AppSec (AppSec atento a PII/secrets)
