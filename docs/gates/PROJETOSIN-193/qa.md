---
card: PROJETOSIN-193
pr: 12
veredicto: FAIL
agente: qa
data: 2026-08-10
tip: a91c1e8cf
ci: vitest pentest-ipc+electron-hooks-status (31 passed); typecheck FAIL (ubuntu CI Lint); boot-log regressão OK
repo: klebersjunior/OpenHands
branch: feat/fase3-electron-ipc-193
---

# QA — PROJETOSIN-193 (Electron Docker/ADB IPC)

**Veredicto:** FAIL

**Revisor:** QA gate (≠ autor DevOps/Backend). Tip `a91c1e8cf`. Spec `docs/specs/fase-3/193-electron-docker-adb-ipc.md` · PR [#12](https://github.com/klebersjunior/OpenHands/pull/12).

**AppSec:** PASS (`docs/gates/PROJETOSIN-193/appsec.md`) — residual MEDIUM/LOW não bloqueiam AppSec.

**Mergeable (eixo QA):** **não** — AC-193-6 falha: `npm run lint` / `tsc` vermelho no CI ubuntu. Tech Lead **não** deve aprovar merge até typecheck verde + re-gate QA.

## Escopo

- Guards/parsers IPC Electron (`electron/pentest-ipc/*`, preload, wiring `main.mjs`)
- Helper browser-safe `src/api/pentest/electron-hooks-status.ts`
- Testes `__tests__/electron/pentest-ipc.test.ts`, `__tests__/api/pentest/electron-hooks-status.test.ts`
- Regressão `boot-log:*` / `desktopBoot` vs `pentestNative`

## Critérios de aceite

| AC | Status | Evidência |
|----|--------|-----------|
| AC-193-1 | PASS | PoC QA próprio: 7 canais (`docker:compose:*`, `adb:*`) com flag off → `hooks_disabled` / 403; `spawn_count === 0`. Vitest AC-193-1. Non-Electron / public → `arePentestHooksEnabled` false. |
| AC-193-2 | PASS | PoC: status disabled `{ enabled:false, dockerAvailable:false, adbAvailable:false, version:"1" }` sem spawn; com flag on `enabled:true` + probes (binários ausentes → available false). Vitest AC-193-2. |
| AC-193-3 | PASS* | PoC: `/evil/elsewhere` → `path_not_allowed`; `..` que escapa root → `path_not_allowed`; `isPathInsideRoot('/allowed/root/../secret', …)` false. Residual (AppSec LOW): `proj/../sib` **dentro** do root ainda `ok:true` — escape pós-resolve coberto; rejeição literal de todo token `..` não implementada. |
| AC-193-4 | PASS | PoC: `parseAdbDevices` estável; `assertAdbSerial('bad;rm')` → `invalid_serial`; Vitest disconnect inválido sem spawn. |
| AC-193-5 | PASS | PoC fonte: `pentest-preload.cjs` só `pentestNative` + 1× `require("electron")`; sem `child_process`/`process.env`. `preload.cjs` mantém `desktopBoot` / `boot-log:` e **não** expõe `pentestNative`. |
| AC-193-6 | **FAIL** | Vitest local 31/31 sem Docker/ADB, **mas** CI `test-and-build (ubuntu)` → Lint/`tsc` **FAILURE** (job `93585716137`, run `31428442793`). Type errors em `__tests__/electron/pentest-ipc.test.ts` e `src/api/pentest/electron-hooks-status.ts`. |

\* AC-193-3 alinhado ao residual AppSec LOW; não é o motivo do FAIL deste laudo.

## Regressão boot-log / desktopBoot

**PASS** — inspeção estática tip `a91c1e8cf`:

- Loading window: `preload: …/preload.cjs`; handlers `boot-log:set-expanded|copy|quit` + sends `boot-log:batch|fatal` intactos; guard `isLoadingWinEvent`.
- Main window: `preload: …/pentest-preload.cjs` (comentário explícito: não mesclar com splash).
- `registerPentestIpc` registrado **após** handlers boot-log; superfícies isoladas.
- Vitest: “loading preload still owns desktopBoot / boot-log only”.

## Regressão CI / lint

| Check | Resultado |
|-------|-----------|
| `npx vitest run __tests__/electron/pentest-ipc.test.ts __tests__/api/pentest/electron-hooks-status.test.ts` | **31 passed** (worktree QA) |
| CI ubuntu `npm run lint` (`react-router typegen && tsc`) | **FAIL** — ver erros abaixo |
| CI windows `test-and-build` | SUCCESS (não anula falha ubuntu) |
| ESLint em `electron/pentest-ipc` (fora do `eslint src` do script lint) | prettier noise em `.mjs` — **fora** do path CI atual; não é o blocker |
| `pr-title` conventional | FAILURE no PR — processo/título; fora do escopo AC funcional |

### Erros `tsc` que bloqueiam AC-193-6 (amostra CI)

`__tests__/electron/pentest-ipc.test.ts`:

- `getMainWebContents` / `projectDir` “não existem” no tipo inferido dos `.mjs` (JSDoc/exports tipados de forma estreita demais ou ausente)
- Discriminated unions: `.code` em resultados de `assertAdbConnectTarget` / `buildComposeArgv`
- Mock `spawnFn` / `EventEmitter` sem `stdout`/`stderr`/`kill`; params `channel`/`fn` implícitos `any`

`src/api/pentest/electron-hooks-status.ts`:

- `(globalThis as Window)` inválido sob `tsc` Node/DOM overlap — sugerido `as unknown as Window` ou narrow via `typeof window`

## Ação requerida (executor DevOps/Backend)

1. Corrigir typecheck: tipagem JSDoc nos módulos `electron/pentest-ipc/*.mjs` **e/ou** casts/narrowing nos testes; cast seguro em `electron-hooks-status.ts`.
2. Confirmar localmente: `npm run typecheck` (ou `npm run lint`) verde **e** os 31 vitest.
3. Pedir **re-gate QA** no tip corrigido (não auto-assinar).
4. Label `Blocked` permanece até QA PASS.

## Residual (não bloqueia sozinho)

- AC-193-3 literal “path com `..` rejeitado” vs aceitar `..` colapsado dentro do root — AppSec LOW; documentar ou rejeitar tokens `..` se TL quiser aderência literal.
- Symlink / TOCTOU (AppSec MEDIUM) — fora do FAIL QA.

## Conclusão para Tech Lead

| Gate | Status |
|------|--------|
| AppSec | PASS |
| QA | **FAIL** |
| Design | N/A |

**Pode aprovar merge?** **Não** — falta QA PASS após fix de typecheck/CI.
