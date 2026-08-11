# Specs — Fase 4 Orquestração avançada (PROJETOSIN-181)

**ADR:** [0001](../../adrs/0001-plataforma-pentest-ia-extensao-openhands.md) (accepted)  
**Blueprint:** §5.2 MCP/microagents · §5.3 mcp-engine · §6.3 Rede · §10 observabilidade — [blueprint](../../product/blueprint-plataforma-pentest-ia.md)  
**Base git:** fork `klebersjunior/OpenHands` tip `e32b31018` (Fases 0–3 Done)

## Fora de escopo (Fase 4 / ADR)

- Farm Corellium / Genymotion / farm remoto
- IPA / iOS
- Kubernetes / RemoteRuntime
- LLM self-hosted (Ollama/vLLM)
- METATRON como motor (só referência de pipeline)
- PentestGPT SaaS (dados fora do engagement)

## Cards

| Card | Spec | Branch | Worktree | Agente(s) |
|------|------|--------|----------|-----------|
| PROJETOSIN-197 | [197-mcp-engine-pentestagent-cai.md](./197-mcp-engine-pentestagent-cai.md) | `feat/fase4-mcp-engine-197` | `.tmp/worktrees/197` | backend (lead) + devops |
| PROJETOSIN-199 | [199-observability-signoz-custody.md](./199-observability-signoz-custody.md) | `feat/fase4-observability-199` | `.tmp/worktrees/199` | devops (lead) + backend |
| PROJETOSIN-198 | [198-mcp-network-runtime.md](./198-mcp-network-runtime.md) | `feat/fase4-mcp-network-198` | `.tmp/worktrees/198` | backend (lead) + devops |
| PROJETOSIN-196 | [196-orchestrator-playbooks.md](./196-orchestrator-playbooks.md) | `feat/fase4-orchestrator-196` | `.tmp/worktrees/196` | backend (lead) → frontend |

## Paralelismo

```
197 mcp-engine (contrato + adapters) ──┐
                                       ├──► 196 orquestrador / playbooks (após contrato estável ou stubs)
198 mcp-network (compose + tools)  ────┘     (pode iniciar em paralelo se só consumir interface §197)

199 SigNoz + chain of custody ───────────── independente (menor acoplamento)
```

- **Wave 1 (agora):** 197 + 199 em worktrees isoladas; 198 pode entrar na mesma wave (runtime/compose isolado de `mcp-engine`).
- **Wave 2:** 196 — implementação de orquestração **depois** do contrato `engine_*` de 197 estável na branch/PR (stubs do contrato nesta pasta já bastam para esqueleto).
- PRs **somente** no fork `klebersjunior/OpenHands`. Gates: **AppSec crítico em 197/198** → QA → AppSec; Design só se UI de 196; **sem auto-assinatura**.

## Dependências cruzadas

```
Findings Service (master) + normalize/post_finding ──► 197 / 198 / 196
PENTEST_AUTONOMY_MODE + confirmation.py (187/195) ──► 197 / 198 / 196
EngMgr compose templates (network stub) ──► 198 materializa runtime Rede
Event stream OpenHands + engagement_id ──► 199 OTEL → SigNoz
Capability RBAC (182) ──► novas caps network/engine se necessário
```

## Segurança (lembrete global)

- Autonomia **server-side only** via `PENTEST_AUTONOMY_MODE` — **nunca** confiar `autonomy_mode` / `engine` em args MCP do cliente/agente para bypass de gate.
- Allowlist de escopo (`PENTEST_SCOPE_ALLOWLIST`) fail-closed; Metasploit/OpenVAS/nmap só contra alvos in-scope.
- Motores (PentestAgent/CAI) rodam em containers do engagement; LLM só via LiteLLM → provedores empresariais (sem Ollama).
- Telemetria 199: **sem** secrets, tokens, API keys, corpos de credencial; prompts LLM só resumo/redacted.
- MCP intrusive (exploit, MSF sessions, GVM full scan) → `confirmation_required` em semi; max-risk policy em autonomous.

## CI (contexto)

- Polyfill `ProgressEvent` / ubuntu Test — já em main.
- mock-llm teste 124 flaky residual — não bloquear merge Fase 4 se flaky isolado documentado.
