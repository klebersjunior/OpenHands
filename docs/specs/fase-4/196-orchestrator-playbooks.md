# Spec Técnica — PROJETOSIN-196: Orquestrador de fases + playbooks multi-agent

**ADR:** docs/adrs/0001-plataforma-pentest-ia-extensao-openhands.md (accepted) — blueprint Orchestrator + §5.2 microagents  
**Card Plane:** PROJETOSIN-196 — `7fe0cb9d-2f48-4447-a2f4-19884f23260d`  
**Agentes:** backend (lead) → frontend (UI mínima de fase/playbook)  
**Prioridade:** P0 após contrato 197  
**Base git:** `e32b31018`  
**Branch:** `feat/fase4-orchestrator-196`  
**Worktree:** `.tmp/worktrees/196`  
**PR target:** fork `klebersjunior/OpenHands` only  
**Depende de:** contrato tools `engine_*` em [197](./197-mcp-engine-pentestagent-cai.md) (stubs OK para esqueleto)

---

## Objetivo

Orquestrar o pipeline **recon → scan → analyze → exploit** por engagement, com **playbooks** multi-agent / microagents por domínio (Web, Rede, Mobile), respeitando allowlist, RBAC e `PENTEST_AUTONOMY_MODE`. O orquestrador **coordena** (EngMgr + MCP engine + MCP domain servers); **não** reimplementa motores.

---

## Premissas

1. Contrato 197 (`engine_start_phase`, `engine_get_run`, `engine_list_playbooks`, …) é a API de motores; orquestrador pode também invocar MCP de domínio (`mcp-recon`, `mcp-webscan`, `mcp-network`, …) conforme playbook.
2. Autonomia **só** server-side; UI apenas exibe/seleciona modo já persistido (195) e fases.
3. Achados continuam no Findings Service — orquestrador agrega `finding_ids` / status, não vira master.
4. Microagents = skills/prompt packs + tool allowlists por domínio; não novo runtime Agent Server fork.
5. Wave 2: implementação completa **após** PR 197 abrir com contrato estável; até lá só stubs/client tipado.

---

## Arquitetura

```
UI (fase/playbook) → Orchestrator API (EngMgr ou serviço leve)
                         ├─ playbook runner (state machine)
                         ├─ mcp-engine (197)
                         ├─ mcp-recon / webscan / network / mobile / sast
                         └─ Findings (read status) + custody events (199 se disponível)
```

**Boundary:** implementar runner em **`services/engagement-manager`** (novo package `app/services/orchestrator/`) — evita terceiro serviço Python no MVP. Se EngMgr ficar grande demais, extrair depois (não nesta fase).

---

## Contrato API (EngMgr)

Prefixo sugerido: `/api/engagements/{engagement_id}/orchestration`

| Method | Path | Body / result |
|---|---|---|
| `GET` | `/playbooks` | Lista catálogo (merge local + `engine_list_playbooks`) |
| `POST` | `/runs` | `{ playbook_id, domain?, engine_id?, start_phase? }` → `{ run_id, status }` |
| `GET` | `/runs/{run_id}` | Estado + fase atual + steps[] + finding_ids |
| `POST` | `/runs/{run_id}/advance` | Avança fase se gates OK / confirmation |
| `POST` | `/runs/{run_id}/cancel` | Cancela |
| `GET` | `/runs` | Lista runs do engagement |

Auth: session API key + capability mínima `pentest.engagement.view` (read) / `pentest.scan.passive` (start). Exploit steps exigem `pentest.exploit.active`.

### Playbook document (YAML/JSON no repo)

```json
{
  "id": "web-passive-mvp",
  "title": "Web passive recon+scan",
  "domain": "web",
  "engine_id": "pentestagent",
  "phases": [
    { "id": "recon", "tools": ["engine_start_phase"], "engine_phase": "recon" },
    { "id": "scan", "tools": ["engine_start_phase"], "engine_phase": "scan", "gate": "none" },
    { "id": "analyze", "tools": ["engine_start_phase"], "engine_phase": "analyze" },
    { "id": "exploit", "tools": ["engine_start_phase"], "engine_phase": "exploit", "gate": "confirmation" }
  ]
}
```

Catálogo MVP mínimo (arquivos em `services/engagement-manager/app/playbooks/`):

| id | domain | Notas |
|---|---|---|
| `web-passive-mvp` | web | até analyze; exploit opcional gated |
| `network-discovery-mvp` | network | usa mcp-network quando 198 disponível; senão skip/mark `blocked_missing_server` |
| `mobile-static-mvp` | mobile | referencia mcp-mobile existente (MobSF static) |

### State machine

`pending` → `running` → `awaiting_confirmation` → `running` → `succeeded` \| `failed` \| `cancelled`

Persistir runs na DB do EngMgr (tabela `orchestration_runs` + `orchestration_steps`).

---

## Microagents / skills

- Packs em `.openhands/skills/` ou `services/engagement-manager/app/microagents/` com system prompt suffix por domínio.
- Na criação/advance de run: anexar suffix ao agent context **ou** documentar ativação via skill id na conversation pentest (preferir skill files versionados + README de wiring; UI pode só selecionar playbook).
- Tool allowlist por domínio: Web → recon+webscan+engine; Rede → network+engine; Mobile → mobile+engine.

---

## Frontend (após API estável)

Escopo UI **mínimo** (HeroUI + i18n):

1. Painel/seção em engagement ou conversation pentest: seletor de playbook + botão Start / Cancel.
2. Timeline de fases (status chips) + link para findings filtrados do run.
3. Quando `awaiting_confirmation`: CTA reutilizando padrão de confirmation já existente (195/187) — **não** novo canal inseguro.
4. Strings via `I18nKey` + `translation.json`; `npm run make-i18n`.
5. Sem magic strings; sem import `react-router` em `src/components/`.

Design: reutilizar tokens; se layout novo não trivial, pedir gate Design. MVP pode ser painel compacto sem marketing.

---

## Integração 197 / 198 / 199

| Dep | Uso |
|---|---|
| 197 | Client stdio/HTTP wrapper chamando tools `engine_*` (subprocess MCP ou API interna se exposta) |
| 198 | Playbook network chama tools `net_*` quando server registrado |
| 199 | Emitir `pentest.engine.run` / custody append em transitions (helper no-op se 199 não merged) |

Desenvolver contra **stubs** do contrato 197 até a branch 197 existir; CI unitária com fake engine.

---

## AC testáveis

| ID | Critério |
|---|---|
| AC-196-1 | `POST /runs` com playbook válido cria run `running`/`pending` e persiste steps |
| AC-196-2 | Fase com `gate: confirmation` em semi → run `awaiting_confirmation` sem chamar exploit |
| AC-196-3 | Allowlist violada em step → step `failed` + código `scope_violation`; run não avança silenciosamente |
| AC-196-4 | Cancel marca run `cancelled` e propaga cancel ao engine stub |
| AC-196-5 | Catálogo GET lista playbooks MVP |
| AC-196-6 | UI: Start playbook + ver fases (teste componente) com i18n keys |
| AC-196-7 | Sem capability exploit, playbook que exige exploit não inicia essa fase |

---

## Gates

| Gate | Foco |
|---|---|
| Design | Se UI nova além de chips/botões simples |
| QA | AC-196-* + regressão engagement |
| AppSec | AuthZ nas rotas; sem bypass autonomia via body; path traversal em playbook id |

Ordem sugerida de gates no PR: QA → AppSec (→ Design se aplicável).

---

## Fora de escopo

- Implementar adapters PentestAgent/CAI (197)
- Implementar nmap/GVM/MSF (198)
- Dashboards SigNoz (199)
- Multi-tenant scheduler global / fila distribuída
- Kubernetes

---

## Entrega

1. Backend orquestrador + testes no worktree 196  
2. Frontend mínimo após contrato API  
3. PR fork `Plane: PROJETOSIN-196`  
4. Comentário Plane; gates sem auto-assinatura
