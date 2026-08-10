---
card: PROJETOSIN-194
pr: 14
veredicto: PASS
agente: appsec
data: 2026-08-10
tip: ecb4db6b4
ci: npm-audit-high-clean; review manual physical-device + pentestNative contract (193)
repo: klebersjunior/OpenHands
branch: feat/fase3-physical-device-194
---

# AppSecurity — PROJETOSIN-194 (Device Android físico + reconexão ADB)

**Veredicto:** PASS

**Revisor:** AppSec gate (≠ autor). Implementação: Backend @ tip feature `a4e0ade87` (+ QA `ccdce96a5` + este laudo). Este laudo **não** auto-assina QA nem Design. Spec `docs/specs/fase-3/194-physical-android-device.md` · QA PASS em `docs/gates/PROJETOSIN-194/qa.md` · PR [#14](https://github.com/klebersjunior/OpenHands/pull/14).

**Mergeable (eixo AppSec):** sim — sem critical/high; residuals MEDIUM/LOW não bloqueiam. Design leve: N/A (UI status mínima na aba Emulador já gated; sem gate Design obrigatório neste card).

## Escopo

Consumo do contrato `window.pentestNative` (PROJETOSIN-193) para device físico + reconnect:

- `src/api/pentest/physical-device-service.ts` + `physical-device-types.ts`
- Cherry-pick tipos/helper 193: `src/types/pentest-native.d.ts`, `src/api/pentest/electron-hooks-status.ts`
- UI mínima: `physical-device-status.tsx` + mount em `emulator-panel.tsx`
- Metadata: `conversation-metadata-store` (`physical_device_*`, `pentest_adb_target`)
- Docs Opção B: `services/mcp-servers/README.md` (`ADB_HOST=host.docker.internal`)
- **Sem** delta `electron/pentest-ipc/*` / preload neste PR (allowlist 193 não reimplementada aqui)

Worktree `.tmp/worktrees/194` @ tip `ecb4db6b4`. Contrato IPC de enforcement permanece no card 193 (AppSec PASS tip `34fc61adb`).

## Checklist

- [x] Sem segredos versionados / hardcoded no delta (metadata localStorage sem tokens; README só documenta env)
- [x] `npm audit --audit-level=high` — **0 high/critical** (4 moderate pré-existentes: dompurify/electron — fora do delta 194)
- [x] Unavailable sem hooks: `hasPentestNativeBridge()` / `enabled === false` → `unavailable`; UI só empty `physical-device-unavailable` (sem select/TCP/connect)
- [x] Mutators IPC só `devices|connect|disconnect|waitForDevice` + `getStatus`; **zero** `adb.shell` / `install` / `dockerCompose.*` no service/UI
- [x] Tipos `pentest-native.d.ts` **idênticos** ao worktree 193 (hash match) — sem ampliar contrato tipado
- [x] Helper `electron-hooks-status.ts`: só lê `getStatus`; diff cosmético vs 193 (inline bridge vs helper local) — **sem** HTTP sidecar / spawn no renderer
- [x] Sem arquivos `electron/` neste PR → **não regressa** allowlist argv / path-policy / sender guard de 193
- [x] Aba Emulador continua atrás de `useHasPentestCapability("pentest.mobile.dynamic")` (tabs/context-menu)
- [x] Serial/host/port: persistência client-only; sanitização load-bearing no main 193 (`assertAdbConnectTarget` / `assertAdbSerial`); UI `parseHostPort` valida faixa de porta
- [x] Opção B documentada — shell/install permanecem em mcp-mobile via ADB TCP genérico (não IPC)

## Controles verificados (gate não-vácuo)

| Controle | Evidência | Tentativa de vacuidade |
|----------|-----------|-------------------------|
| Sem hooks → unavailable | `getPhysicalDeviceAvailability` + testes AC-194-1; UI ramo unavailable sem controles | Remover check → Vitest falha; UI ofereceria connect. **Controle real.** |
| Sem verbos perigosos | Grep produção: só `api.adb.devices/connect/disconnect/waitForDevice`; tipos sem `shell`/`install` | Tipos ambient incluem `dockerCompose` (paridade 193) mas **194 não chama** — superfície runtime = preload 193 |
| Allowlist 193 intacta | Diff PR sem `electron/pentest-ipc`; tipos hash-igual 193 | N/A neste card — enforcement no main |
| Host/serial injection | Main 193: charset host/IP, porta 1–65535, serial `[A-Za-z0-9._:-]+`, bloqueio `@` | Cliente 194 não revalida charset do host antes do IPC (ver LOW) |
| AuthZ / public | Bridge ausente em browser/`--public` sem preload → unavailable; sem bake de session key neste delta | Capability só UI (residual MEDIUM herdado) |
| XSS metadata/UI | React text nodes para serial/erro; sem `dangerouslySetInnerHTML` | OK |

## Findings

### Critical / High

Nenhum. **Sem bloqueio.**

### MEDIUM — Capability `pentest.mobile.dynamic` só na UI (herdado)

Aba Emulador (e portanto `PhysicalDeviceStatus`) gated em `conversation-tabs` / context-menu. Com hooks Electron **on**, XSS na origem Canvas ainda pode chamar `window.pentestNative.adb.*` allowlisted (mesmo threat model 193: compose/ADB opt-in).

**Decisão:** residual MEDIUM alinhado a AppSec 192/193 — não FAIL. Follow-up: AuthZ de capability server-side / EngMgr quando RBAC multi-role for load-bearing.

### LOW — Validação de host no cliente mais frouxa que o main

`parseHostPort` aceita host não-vazio + porta 1–65535; não replica `assertAdbConnectTarget` (charset IP/hostname, ban `@`/`/`/` `). Inputs maliciosos falham no IPC 193 (`invalid_host`) — defense-in-depth client ausente.

**Decisão:** residual LOW; opcional espelhar regex 193 no service antes do IPC.

### LOW — Teste AC-194-5 só no mock surface

Vitest “does not expose shell or install” inspeciona keys do mock; cobertura real = tipos + grep de produção (já feitos neste gate).

## Dependências

`npm audit --audit-level=high`: **PASS** (0 high/critical). Moderates pré-existentes (dompurify via monaco/posthog; electron GHSA-r4w5-6pfg-jxp5) — sem bump exigido por este card.

## Evidência

- Tip: `ecb4db6b4` (feature `a4e0ade87` + QA + AppSec laudo)
- QA: PASS (`docs/gates/PROJETOSIN-194/qa.md`)
- Cherry-pick: `pentest-native.d.ts` idêntico a 193; helper status semanticamente equivalente
- Dependência 193: AppSec PASS + allowlist ADB `devices|connect|disconnect|wait-for-device`
- Plane: label `Blocked` removida após PASS

## Ação requerida

1. **PASS** — label `Blocked` removida no Plane.
2. Tech Lead: merge liberado no eixo **AppSec + QA** neste tip (`ecb4db6b4` ou successor que preserve os controles). Design leve **N/A**.
3. Residuals MEDIUM/LOW → backlog; não bloqueiam PROJETOSIN-194.
4. Garantir que PR #12 (193) / allowlist main esteja mergeada ou disponível na base antes de confiar no IPC em runtime Desktop.
Review GitHub: COMMENT (APPROVE bloqueado — mesmo account do autor do PR).
