---
card: PROJETOSIN-189
pr: 6
veredicto: PASS
agente: qa
data: 2026-08-10
tip: a99bb81ee
ci: pytest mcp-sast (10) + findings-service (19) + vitest use-pentest-capabilities (4)
repo: klebersjunior/OpenHands
branch: feat/fase1-mcp-sast-dd-189
---

# QA — PROJETOSIN-189 (mcp-sast + DefectDojo one-way sync)

**Veredicto:** PASS

**Revisor:** QA gate (não autor do código). AppSec **não** assinado neste laudo.

## Escopo

Spec `docs/specs/fase-1/189-mcp-sast-defectdojo.md` — AC-189-A1…A4 e B1…B5.
Worktree `.tmp/worktrees/189` @ `a99bb81ee` (PR #6).

## Critérios de aceite

| AC | Status | Evidência |
|----|--------|-----------|
| AC-189-A1 list_tools Semgrep+Trivy + cap `pentest.sast.run` | PASS | `test_list_tools_exposes_semgrep_and_trivy`; `server.py` registra `@mcp.tool` `sast_semgrep_scan` / `sast_trivy_scan`; `REQUIRED_CAPABILITY == "pentest.sast.run"` |
| AC-189-A2 scan fixture → ≥1 POST Findings c/ severidade | PASS | `test_semgrep_fixture_posts_finding`, `test_trivy_stub_posts_finding` (httpx recording; severity mapeada) |
| AC-189-A3 path fora do workspace → erro, sem POST | PASS | `test_path_outside_workspace_errors_without_post`, `test_trivy_path_traversal_no_post` |
| AC-189-A4 mapeamento severidade Semgrep/Trivy → enum | PASS | `test_map_semgrep_severity`, `test_map_trivy_severity`, `test_normalize_*_payload_from_report` |
| AC-189-B1 sync mock httpx → `defectdojo_id` | PASS | `test_sync_with_httpx_mock_sets_defectdojo_id` (`/api/v2/reimport-scan/`, id 4242) |
| AC-189-B2 status_filter default exclui `new` / FP | PASS | default `["confirmed"]` em `SyncDefectDojoRequest`; `test_status_filter_excludes_new_and_fp_by_default` |
| AC-189-B3 triage FP c/ `defectdojo_id` espelha DD | PASS | `test_triage_fp_mirrors_to_defectdojo` + `test_status_to_dd_map`; router `triage.py` dispara mirror async sem reverter triage local |
| AC-189-B4 sem `DEFECTDOJO_API_TOKEN` → 503 | PASS | `test_sync_without_token_returns_503` |
| AC-189-B5 testes DefectDojo estendidos (não invertidos) | PASS | `tests/test_defectdojo_sync.py` mantém AC legado `test_sync_defectdojo_queues_and_sets_id` + novos B1–B4 |

## Capability mirror TS

`pentest.sast.run` em `services/shared/capabilities.py` e `src/types/pentest-rbac.ts` (admin/pentester). Endpoint capabilities: `test_capabilities_endpoint` (assert inclui `pentest.sast.run`).

## Regressão

```text
services/mcp-servers/mcp-sast/tests:     10 passed
services/findings-service/tests:         19 passed (incl. CRUD/triage + DefectDojo)
__tests__/hooks/use-pentest-capabilities: 4 passed
```

Comandos (worktree 189):

```bash
python -m pytest services/mcp-servers/mcp-sast/tests -v
python -m pytest services/findings-service/tests -v
npx vitest run __tests__/hooks/use-pentest-capabilities.test.tsx
```

Suite npm completa do canvas **não** exigida pela spec (escopo Python); Vitest do hook RBAC rodado porque o PR tocou `src/types/pentest-rbac.ts`.

## Vacuidade / revisão independente

- A1: helper `list_tool_names()` é lista estática; QA confirmou registro real via `@mcp.tool` em `server.py` (se os decorators sumirem, o helper sozinho não falharia — residual fraco, não bloqueante dado A2/A3 comportamentais).
- B1: mock exige Authorization + path `reimport-scan`; se o cliente DD sumir, o teste falha.
- B3: se `mirror_status` deixar de ser chamado no triage com `defectdojo_id`, o mock assert falha; falha de mirror não reverte triage local (código + comentário no router).

## Residual (não bloqueante)

- `list_tool_names` não introspecta o registry FastMCP (ver acima).
- Trivy/Semgrep em CI usam fixture/stub (binários reais só com `MCP_SAST_USE_REAL_BINARIES=1`) — alinhado à spec (mock/fixture).
- AppSec gate **pendente** (este laudo não cobre segurança).

## Review GitHub

Intent: `APPROVE`. GitHub rejeitou (`Review Can not approve your own pull request`) porque a conta `gh` = autor do PR (`klebersjunior`). Foi postado review **COMMENT** com veredicto QA **PASS** explícito. Papel do revisor (QA) ≠ autor Backend do código.

## Ação requerida

Nenhuma para QA. Merge sob Tech Lead após AppSec PASS + este QA PASS.

---

## Addendum — mock-LLM profile-management (2026-08-10)

**Veredicto inicial:** FLAKE determinístico no tip `f992dfaa4` (3× FAIL consecutivos — não flake aleatório).

| Item | Evidência |
|------|-----------|
| Falha | `tests/e2e/mock-llm/settings/mock-llm-profile-management.spec.ts:105` — poll 15s: `"deletion-guard-inactive" should become active after deleting "deletion-guard-active"` |
| Run | https://github.com/klebersjunior/OpenHands/actions/runs/31414303595 @ `f992dfaa4` (59 passed, 1 failed) |
| Contraste | Mesmo teste PASS na run anterior do #6 @ `9b9ee1187` |
| Escopo PR | `git diff 9b9ee1187..f992dfaa4` e `main...HEAD`: **nenhum** arquivo de profile / `useEnsureActiveProfile` / settings LLM |
| Causa | Pós-delete, `expect.poll` fazia `page.goto("/settings/llm")` a cada intervalo — reload abortava a mutation delete/activate de `useEnsureActiveProfile` |

### Hardening aplicado (mesmo PR / branch)

**Veredicto pós-fix:** PASS (hardening de teste; AC intacto).

Mudança em `mock-llm-profile-management.spec.ts` (step pós-delete):

1. Após `delete-profile-confirm`, esperar row ACTIVE sumir via locator/`toHaveCount(0)` **sem reload** (timeout 30s).
2. Confirmar row INACTIVE permanece.
3. Assert `profile-active-badge` first visible (timeout 30s) — mesmo contrato reativo de `activateProfileViaUI`.
4. **Removido** `page.goto` de dentro do poll.

**Rodou local?** Não. Stack mock-LLM inviável neste host Windows: `MOCK_LLM_PYTHON` default `python3` ausente no PATH; `webServer` do Playwright usa shell POSIX (`[ -f build/... ]`, `exec env`). Validação fica no CI do fork após push.

**Ação:** push fork-only; não mergear; não tocar mcp-sast/DD de produção.
