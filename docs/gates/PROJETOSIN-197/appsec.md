---
card: PROJETOSIN-197
pr: 15
veredicto: PASS
agente: appsec
data: 2026-08-10
tip: 1555e4e2ce7f0f3e3e45a376ec679cea9b3d24e4
ci: pytest mcp-engine 45 passed; PoCs HIGH-1/2/3 re-proved closed
repo: klebersjunior/OpenHands
branch: feat/fase4-mcp-engine-197
prior: FAIL @ 5f02d0748 / laudo ccce59ba3
---

# AppSecurity — PROJETOSIN-197 (mcp-engine PentestAgent / CAI) — re-gate

**Veredicto:** PASS

**Revisor:** AppSec gate (≠ autor do fix `1555e4e2c`). Não assina QA. Não mergeia.

**[GITHUB-REVIEW-PENDENTE]** — conta `gh` = autor do PR (`klebersjunior`); review formal REQUEST_CHANGES/APPROVE bloqueada. Veredicto e checklist neste laudo + comentário no PR.

## Escopo (re-gate)

Remediação dos HIGH do laudo FAIL anterior após `1555e4e2c` (`fix(mcp-engine): close AppSec HIGH scope/SSRF/Ollama`).

1. HIGH-1 — targets vazios/None/omitidos → `invalid_targets` (não spawn)
2. HIGH-2 — allowlist positiva `PENTEST_ENGINE_URL_ALLOWLIST`; rejeita 127.1, metadata, link-local
3. HIGH-3 — OLLAMA_* / LITELLM localhost:11434 → `self_hosted_llm_forbidden`
4. Residuais MEDIUM do laudo FAIL (não bloqueantes)

Worktree `.tmp/worktrees/197` @ `1555e4e2c`. PR https://github.com/klebersjunior/OpenHands/pull/15

## Checklist

- [x] Sem segredos LiteLLM / `SESSION_API_KEY` hardcoded no delta mcp-engine
- [x] Compose engine sem `docker.sock` / sem `network_mode: host` / sem privileged
- [x] Achados via `normalize_finding` + `FindingsClient`
- [x] Confirmation: `engine_exploit` ∈ `ACTIVE_TOOLS`; fase `exploit` → `require_confirmation`
- [x] **PASS** Escopo: `targets` vazio/`None`/omitido/`""` → `invalid_targets`; zero posts Findings
- [x] **PASS** SSRF: allowlist positiva + bloqueio loopback/link-local/metadata/`127.1`/`0.0.0.0`/userinfo/https
- [x] **PASS** Ollama: `OLLAMA_HOST` / `LITELLM_BASE_URL` com `localhost:11434` → `self_hosted_llm_forbidden`
- [ ] Autonomia nested / chaves LLM em `options` — residual MEDIUM (inalterado)

## Fechamento dos HIGH (PoCs re-provados)

### HIGH-1 — CLOSED

**Controle:** `tools/start_phase.py` exige ≥1 target não-vazio antes de `assert_in_scope` / `registry.create`.

**PoC @ `1555e4e2c`:**

| Input | Resultado |
|-------|-----------|
| `targets=[]` | `ok=false` `error=invalid_targets` posts=0 |
| `targets=None` | `ok=false` `error=invalid_targets` posts=0 |
| omitido | `ok=false` `error=invalid_targets` posts=0 |

Teste anti-vácuo: `test_high1_empty_or_omitted_targets_fail_closed`.

### HIGH-2 — CLOSED

**Controle:** `assert_allowed_engine_url` — scheme `http` only, sem userinfo, denylist metadata/loopback via `ipaddress` (incl. `127.1`, decimal IPv4), allowlist positiva `PENTEST_ENGINE_URL_ALLOWLIST` (fail-closed se vazia). Wired em `PentestAgentAdapter` / `CaiAdapter` (`status` + `_run_remote`). Compose injeta DNS do projeto.

**PoC @ `1555e4e2c`:**

| URL | Bloqueada? |
|-----|------------|
| `http://127.0.0.1:9999` | sim |
| `http://127.1:9999` | **sim** |
| `http://0.0.0.0:9999` | **sim** |
| `http://169.254.169.254/...` | **sim** |
| `http://metadata.google.internal/` | **sim** |
| `http://engine-pentestagent:8080` (allowlisted) | não |

### HIGH-3 — CLOSED

**Controle:** `assert_no_ollama_llm` — qualquer `OLLAMA_*` setado rejeita; bases LLM com host loopback + porta 11434 ou hostname contendo `ollama` rejeitam. `start_phase` retorna `self_hosted_llm_forbidden` antes do spawn.

**PoC @ `1555e4e2c`:**

| Env | Resultado |
|-----|-----------|
| `OLLAMA_HOST=http://localhost:11434` | `self_hosted_llm_forbidden` |
| `LITELLM_BASE_URL=http://localhost:11434` | `self_hosted_llm_forbidden` |
| `OLLAMA_HOST=http://127.0.0.1:11434` | `self_hosted_llm_forbidden` |
| `LITELLM_BASE_URL=https://litellm.heimdallsec.example/v1` | permitido |

## Residuais (não bloqueiam)

### MEDIUM-1 — `options` nested / LLM override

Top-level `options.autonomy_mode` rejeitado. Nested `options.config.autonomy_mode` e chaves `LITELLM_*` / `llm_base_url` em `options` ainda podem ser encaminhadas ao motor remoto. Elevar a HIGH se o contrato do motor real preferir `options` ao env.

### MEDIUM-2 — Compose scope allowlist CSV vs JSON

`PENTEST_SCOPE_ALLOWLIST` via CSV no parser; template histórico com `tojson` em outros fluxos. Neste tip, `PENTEST_ENGINE_URL_ALLOWLIST` no compose é CSV de hostnames do projeto (OK). Manter alinhamento CSV único.

### LOW — `engagement_id` fallback em `options` / `"unknown"`

Correlação spoofável; não RCE.

## Controles OK (mantidos)

| Controle | Evidência |
|---|---|
| Autonomia top-level | `invalid_options` se `options.autonomy_mode` |
| Exploit confirmation | AC-197-3 testes verdes |
| Findings master | sem DefectDojo/METATRON adapter |
| Compose superfície | bridge; sem sock/host/privileged |
| CAI opt-in | flag off → `engine_not_enabled` |

## Dependências

Delta Python (`services/mcp-servers/mcp-engine`). `npm audit` N/A neste PR. Suíte local: **45 passed**.

## Ação

**AppSec PASS** — HIGH-1..HIGH-3 fechados com testes anti-remoção. Label `Blocked` removida no Plane.

Tech Lead: merge só com QA PASS + este AppSec PASS. **Não mergeado por AppSec.**
