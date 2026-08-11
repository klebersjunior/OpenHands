---
card: PROJETOSIN-197
pr: 15
veredicto: FAIL
agente: appsec
data: 2026-08-10
tip: 5f02d0748669ad835cdb0820acce5ab4b240b524
ci: pytest mcp-engine local PoCs; npm audit N/A (delta Python)
repo: klebersjunior/OpenHands
branch: feat/fase4-mcp-engine-197
---

# AppSecurity — PROJETOSIN-197 (mcp-engine PentestAgent / CAI)

**Veredicto:** FAIL

**Revisor:** AppSec gate (≠ autor do commit de implementação). Não assina QA. Não mergeia.

## Escopo

Spec `docs/specs/fase-4/197-mcp-engine-pentestagent-cai.md` + foco obrigatório do gate crítico:

1. Escopo fail-closed (`PENTEST_SCOPE_ALLOWLIST`) / bypass
2. Autonomia server-side (`PENTEST_AUTONOMY_MODE`); rejeição de override em args/options
3. SSRF / URL do motor (loopback, hosts internos, allowlist)
4. Sem Ollama / self-hosted LLM; sem METATRON como motor
5. Secrets (LiteLLM / `SESSION_API_KEY`) — sem hardcode; logs sem dump
6. Confirmation gate em fase `exploit` (`engine_exploit` / `ACTIVE_TOOLS`)
7. Superfície Docker/compose (sem `docker.sock`, sem host network)
8. Achados só via Findings master

Worktree `.tmp/worktrees/197` @ `5f02d07`. PR https://github.com/klebersjunior/OpenHands/pull/15

## Checklist

- [x] Sem segredos LiteLLM / `SESSION_API_KEY` hardcoded no delta mcp-engine (pins só tags em `config/defaults.json`)
- [x] Compose engine sem `docker.sock` / sem `network_mode: host` / sem privileged
- [x] Achados via `normalize_finding` + `FindingsClient` (sem DefectDojo / METATRON adapter)
- [x] Confirmation: `engine_exploit` em `ACTIVE_TOOLS`; fase `exploit` chama `require_confirmation`
- [ ] **FAIL** Escopo: `targets` vazio/`None` ignora allowlist e ainda spawna run
- [ ] **FAIL** SSRF URL do motor: só denylist de 3 hostnames loopback; sem allowlist positiva; metadata / `127.1` passam
- [ ] **FAIL** Ollama: `http://localhost:11434` e variantes sem substring `ollama` não são rejeitadas
- [ ] Autonomia: top-level `options.autonomy_mode` rejeitado; nested / chaves LLM em `options` passam ao adapter (residual)

## Findings

### HIGH-1 — Bypass de escopo via `targets` vazio ou omitido (BLOCK)

**Onde:** `tools/start_phase.py` — loop `for target in target_list` só valida entradas presentes.

**PoC (local, tip `5f02d07`):** com `PENTEST_SCOPE_ALLOWLIST=example.com`, `engine_start_phase(..., targets=[])` e `targets=None` retornam `ok: true` / `status: succeeded` e postam finding (mock). Zero `scope_violation`.

**Por que bloqueia:** Spec/AC-197-2 exigem fail-closed; motor não pode mirar fora do escopo. Omitir targets esvazia o gate — asserção “todo target passou por `assert_in_scope`” torna-se vácua quando a lista é vazia.

**Remediação:** Exigir ≥1 target in-scope antes de criar/spawnar run; rejeitar `targets` ausente/vazio com `scope_violation` (ou erro tipado equivalente fail-closed). Teste negativo que falhe se o controle sumir.

### HIGH-2 — SSRF do control-plane incompleto (BLOCK)

**Onde:** `adapters/pentestagent.py` / `adapters/cai.py` — `_is_loopback_url` só marca `127.0.0.1` | `localhost` | `::1`. `_run_remote` faz `httpx` POST para qualquer outra URL de env.

**PoC hostname check:**

| URL | Bloqueada? |
|-----|------------|
| `http://127.0.0.1:9999` | sim |
| `http://127.1:9999` | **não** |
| `http://0.0.0.0:9999` | **não** |
| `http://169.254.169.254/...` | **não** |
| `http://metadata.google.internal/` | **não** |
| `http://engine-pentestagent:8080` | não (esperado se allowlisted) |

**Por que bloqueia:** Foco obrigatório pede allowlist (loopback + hosts internos). Só denylist literal não impede metadata link-local nem encodings de loopback. Sem allowlist positiva (ex. hostname do serviço compose / rede do engagement), misconfig de env vira SSRF server-side.

**Remediação:** Allowlist positiva de hosts/schemes (`http` only + nomes compose / DNS interno do engagement); rejeitar link-local (`169.254.0.0/16`, `fe80::/10`), loopback por `ipaddress` (não só strings), e URLs com userinfo ambíguo. Testes que quebrem se allowlist for removida.

### HIGH-3 — Guard anti-Ollama / self-hosted furável (BLOCK)

**Onde:** `adapters/base.py` — `assert_no_ollama_llm()`.

**PoC:**

- `OLLAMA_HOST=http://localhost:11434` → **não** rejeita (`None`)
- `LITELLM_BASE_URL=http://localhost:11434` → **não** rejeita
- `OLLAMA_HOST=http://127.0.0.1:11434` → rejeita (substring/`11434` path parcial)

**Por que bloqueia:** Spec proíbe Ollama/self-hosted. `localhost:11434` é o default canônico do Ollama e passa no gate.

**Remediação:** Parse de host/porta; bloquear `localhost`/`127.0.0.0/8`/`::1` + porta 11434; bloquear hostname contendo `ollama`; preferir allowlist de bases LiteLLM empresariais. Cobrir com teste que falhe se só o check de substring existir.

### MEDIUM-1 — `options` nested / LLM override não filtrados

Top-level `options.autonomy_mode` é rejeitado (bom; testado). Nested `options.config.autonomy_mode` e chaves `LITELLM_BASE_URL` / `llm_base_url` em `options` são aceitas e encaminhadas em `_run_remote` body. Quando o motor real preferir `options` ao env, reabre autonomia/LLM.

**Decisão:** residual MEDIUM até engines reais; elevar a HIGH se o contrato do motor ler autonomia/LLM de `options`.

### MEDIUM-2 — Compose `PENTEST_SCOPE_ALLOWLIST: {{ allow_rules | tojson }}`

`tojson` em lista produz JSON (`["a.com"]`), enquanto `_parse_allowlist` faz `split(",")`. Resultado típico: fail-closed operacional (não match), não bypass aberto. Risco de operadores “consertarem” com allowlist frouxa fora do parser.

**Decisão:** MEDIUM ops/compat — alinhar CSV vs JSON num único contrato.

### LOW — `engagement_id` fallback em `options`

Se `ENGAGEMENT_ID` ausente, `options.engagement_id` ou `"unknown"` é usado. Correlação spoofável; não é RCE.

### Controles OK (não bloqueantes)

| Controle | Evidência |
|---|---|
| Autonomia top-level | `start_phase` rejeita `options.autonomy_mode`; schema MCP sem arg `autonomy_mode` |
| Exploit confirmation | `EXPLOIT_GATE_TOOL="engine_exploit"` ∈ `ACTIVE_TOOLS`; semi sem token → `confirmation_required` (teste AC-197-3) |
| Findings master | adapters usam `FindingsClient.post_finding`; grep sem DefectDojo/METATRON |
| Compose superfície | `compose-engine-runtime.yml.j2`: bridge networks, sem sock/host/privileged |
| Secrets no código | LiteLLM/session via env Jinja; sem hardcode no mcp-engine |
| Eventos | `emit_run_event` sem prompts/secrets |
| CAI opt-in | flag off → `engine_not_enabled` |

## Dependências

Delta é Python (`services/mcp-servers/mcp-engine`). `npm audit --audit-level=high` não cobre este PR; sem novas deps npm no diff. Pins de imagem só tags (sem secrets).

## Ação requerida

**BLOCK merge** até remediar HIGH-1..HIGH-3 e re-gate AppSec (revisor ≠ autor).

1. Fail-closed em `targets` vazio/ausente + teste anti-vácuo  
2. Allowlist positiva + bloqueio link-local/loopback-IP para URL do motor  
3. Fechar bypass Ollama `localhost:11434` / self-hosted loopback  
4. (Recomendado) strip/deny de chaves sensíveis em `options` antes do forward remoto  

**Não mergeado por AppSec.** Tech Lead só mergeia após AppSec PASS + QA.
