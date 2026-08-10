---
card: PROJETOSIN-193
pr: 12
veredicto: PASS
agente: appsec
data: 2026-08-10
tip: 34fc61adb
ci: vitest pentest-ipc+electron-hooks-status (31 passed); npm audit --audit-level=high (0 high/critical)
repo: klebersjunior/OpenHands
branch: feat/fase3-electron-ipc-193
---

# AppSecurity — PROJETOSIN-193 (Electron Docker/ADB IPC)

**Veredicto:** PASS

**Revisor:** AppSec gate (≠ autor). Implementação: DevOps/Backend @ tip `34fc61adb`. Este laudo **não** auto-assina QA. Spec `docs/specs/fase-3/193-electron-docker-adb-ipc.md` · PR [#12](https://github.com/klebersjunior/OpenHands/pull/12).

**Mergeable (eixo AppSec):** sim — sem critical/high; residuals MEDIUM/LOW não bloqueiam. QA pode seguir / Tech Lead merge só com QA PASS + este AppSec PASS no tip.

## Escopo

Superfície Electron IPC ↔ Docker Compose / ADB do host:

- `electron/pentest-ipc/*` (guard, path-policy, spawn-safe, docker-compose, adb, parsers, register)
- `electron/pentest-preload.cjs` + wiring `electron/main.mjs` (main window only)
- `src/api/pentest/electron-hooks-status.ts` (browser-safe, sem HTTP)
- Flag `PENTEST_ELECTRON_HOOKS_ENABLED` (`.env.sample` + `config/defaults.json` roots)
- Testes `__tests__/electron/pentest-ipc.test.ts`, `__tests__/api/pentest/electron-hooks-status.test.ts`
- Regressão: `boot-log:*` / loading `preload.cjs` isolados do pentest preload

## Checklist

- [x] Sem segredos versionados / hardcoded no delta (só documentação de env; PostHog em `defaults.json` pré-existente)
- [x] `npm audit --audit-level=high` — **0 high/critical** (4 moderate pré-existentes: dompurify/electron — fora do delta 193)
- [x] Session key / modo público: hooks off em `--public` / server-only; flag default **off**; sem bake de session key no preload pentest
- [x] Allowlist argv: `docker compose` só `up|down|ps`; ADB só `devices|connect|disconnect|wait-for-device`; `shell: false`; binários fixos (`docker`/`adb`), nunca do renderer
- [x] Path policy: roots `electronComposeRoots` + `OH_CANVAS_SAFE_STATE_DIR`; absolute required; escape via `..` resolvido → `path_not_allowed`; compose file fora dos roots rejeitado
- [x] Sender guard: só `mainWin.webContents` (+ `senderFrame` vs `mainFrame` quando disponível); loading splash não tem `pentestNative`
- [x] Hardening Electron: `contextIsolation: true`, `nodeIntegration: false` na main window; preload expõe só API documentada (sem `process`/`fs`/`child_process`)
- [x] Sem HTTP novo de status (MVP omite sidecar) — reduz superfície
- [x] Output truncado 256 KiB; timeouts; env do child filtrado (sem keys arbitrárias do renderer)
- [ ] Symlink / path inexistente — **MEDIUM residual** (ver abaixo)
- [ ] Kill só do child (não process tree) — **LOW residual**

## Controles verificados (gate não-vácuo)

| Controle | Evidência | Tentativa de vacuidade |
|----------|-----------|-------------------------|
| Flag default off | `arePentestHooksEnabled` exige `=== "true"`; AC-193-1: 7 canais → `hooks_disabled` + **zero** `spawnFn` | Remover check → teste falha (body chamado). **Controle real.** |
| Public / non-desktop | `isPublicServerMode` (`--public`, env server-only); `isElectronDesktop: false` → off | OK |
| Path fora dos roots | AC-193-3 + PoC AppSec: `/evil/elsewhere` → `path_not_allowed`, sem spawn | OK |
| `..` que escapa | `isPathInsideRoot` + resolve; PoC `engagements/../outside` → deny | Comentário em `path-policy` fala em rejeitar tokens `..` **antes** do resolve, mas só bloqueia escape pós-resolve; `proj/../sib` **dentro** do root ainda passa (LOW drift vs AC literal) |
| Sem shell / sem adb shell\|install | `spawn(..., { shell: false })`; verbs allowlisted; grep sem `shell:true` / `adb shell` | OK |
| Preload mínimo | Source + AC-193-5: um `require("electron")`; sem `process.env` / fs | Teste é grep de fonte (fraco), mas arquivo preload é o controle |
| Sender | `event.sender !== mainWc` → `sender_rejected`; loading ≠ main | OK |
| Boot-log intacto | Loading usa `preload.cjs` / `desktopBoot`; main usa `pentest-preload.cjs`; handlers `boot-log:*` intactos | OK |
| Helper browser-safe | `getElectronHooksStatus` só lê `window.pentestNative`; sem fetch/HTTP | OK |

### PoC AppSec (path / symlink)

Worktree tip `34fc61adb`, Node import de `path-policy.mjs`:

| Caso | Resultado |
|------|-----------|
| `projectDir` com `../` escapando root | `path_not_allowed` |
| `projectDir` com `../` colapsando **dentro** do root | `ok: true` (aceito) |
| Path **inexistente** sob root que é symlink | `ok: true` (lexical) — realpath **não** aplicado |
| Path **existente** sob root symlink (realpath fora) | `path_not_allowed` |

Asserção positiva “symlinks que escapem são rejeitados via realpath” é **parcialmente vácua** para paths ainda não criados. Classificado MEDIUM (requer FS local pré-posicionado; renderer XSS sozinho não cria o symlink).

## Findings

### MEDIUM — Symlink / TOCTOU em `projectDir` inexistente

**Arquivo:** `electron/pentest-ipc/path-policy.mjs` (`realpathIfExists`, `resolveComposeRoots`)

- Roots allowlisted **não** são `realpath`’d na resolução.
- Se o path ainda não existe, cai em `resolve(normalize)` sem seguir/rejeitar symlink intermediário ou root-symlink.
- Com hooks **enabled**, `docker compose --project-directory` pode seguir o symlink no spawn.

**Remediação sugerida (não bloqueia este card):** `realpath` dos roots quando existirem; exigir que `projectDir` exista **ou** realpath do ancestral existente + rejeitar se qualquer componente symlink escapar; opcionalmente rejeitar input cru contendo `\0` (já) e segmentos `..` literais.

### MEDIUM — Trust boundary compose sob hooks on

Com `PENTEST_ELECTRON_HOOKS_ENABLED=true`, XSS no Canvas (origem ingress) pode invocar `dockerCompose.up` em qualquer dir sob roots. Compose files trustados podem montar docker.sock / build arbitrário (`up -d` sem `--build` explícito ainda pode buildar se o YAML tiver `build:`).

Aceitável no threat model desktop opt-in; documentar para operadores. Endurecer depois (deny `build:`, no `--pull`, content-hash) se o modelo evoluir.

### LOW — Comentário vs comportamento em `..`

Comentário em `assertAllowedComposePaths` implica rejeição explícita de tokens `..`; implementação só impede escape pós-normalize. Alinhar código ou AC.

### LOW — Timeout kill não é process tree

`spawn-safe` faz `child.kill("SIGKILL")` sem tree-kill; orphans possíveis (DoS/ruído), não RCE.

### LOW — `sandbox: true` não explícito

Default moderno do Electron costuma sandboxar; preferir set explícito na main window.

## Dependências

`npm audit --audit-level=high`: **limpo** de high/critical. Moderates pré-existentes (dompurify via monaco/posthog; electron GHSA-r4w5-6pfg-jxp5) — sem bump exigido por este card.

## Evidência de testes

```
__tests__/electron/pentest-ipc.test.ts
__tests__/api/pentest/electron-hooks-status.test.ts
→ 2 files / 31 tests passed
```

## Ação

1. **PASS** — sem label `Blocked`.
2. Tech Lead: merge somente com **QA PASS** + AppSec PASS neste tip (`34fc61adb` ou successor que preserve os controles).
3. Residuals MEDIUM/LOW → backlog / follow-up; não bloqueiam PROJETOSIN-193.
4. QA pode executar gate de AC/regressão em paralelo ou em seguida.
