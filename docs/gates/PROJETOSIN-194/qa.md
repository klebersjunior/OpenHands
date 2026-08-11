---
card: PROJETOSIN-194
pr: 14
veredicto: PASS
agente: qa
data: 2026-08-10
tip: a4e0ade87
ci: vitest physical-device-service + electron-hooks-status (11 passed)
repo: klebersjunior/OpenHands
branch: feat/fase3-physical-device-194
---

# QA — PROJETOSIN-194 (Device Android físico + reconexão ADB)

**Veredicto:** PASS

**Revisor:** QA gate (≠ autor). Implementação: Backend @ tip `a4e0ade87`. Este laudo **não** auto-assina AppSec nem Design. Spec `docs/specs/fase-3/194-physical-android-device.md` · PR [#14](https://github.com/klebersjunior/OpenHands/pull/14).

**AppSec pode iniciar:** sim — QA PASS no tip acima; AppSec deve validar abuso de hooks / AuthZ da superfície `pentestNative` consumida.

## Escopo verificado

- `src/api/pentest/physical-device-service.ts` + `physical-device-types.ts`
- `src/api/pentest/electron-hooks-status.ts` (contrato 193 cherry-pick)
- `src/types/pentest-native.d.ts` (só `devices|connect|disconnect|waitForDevice`)
- UI mínima: `physical-device-status.tsx` + mount em `emulator-panel.tsx`
- Persistência: `conversation-metadata-store` (`physical_device_*`, `pentest_adb_target`)
- Testes: `__tests__/api/pentest/physical-device-service.test.ts`, `electron-hooks-status.test.ts`

## Critérios de aceite

| AC | Status | Evidência |
|---|---|---|
| AC-194-1 | PASS | Vitest: `unavailable` quando `pentestNative` ausente / `enabled:false`; `listDevices` → `code: unavailable`. UI: ramo `availabilityQuery.data?.status === "unavailable"` renderiza só `data-testid="physical-device-unavailable"` — **sem** select/TCP/connect (`physical-device-status.tsx`). |
| AC-194-2 | PASS | Vitest mock `pentestNative`: lista devices + `persistPhysicalDeviceSelection` grava `physical_device_serial` / host / port / `pentest_adb_target: "physical"` no metadata. |
| AC-194-3 | PASS | Vitest `PhysicalDeviceReconnectMonitor`: sequência `connected` → `disconnected` → `reconnecting` → `connected` com scheduler injetado; `monitor.stop()` — sem reload de conversa/engagement. |
| AC-194-4 | PASS | `nextBackoffMs` teto 30s; loop com device ausente dorme `1s→2→4→8→16→30`. |
| AC-194-5 | PASS | Contrato tipado `PentestNativeApi.adb` sem `shell`/`install`; grep no service/UI só chama `devices`/`connect`/`disconnect`/`waitForDevice`. (Nota: teste unitário “surface” só valida o mock — reforçado por análise estática do código de produção.) |

## Regressão

| Suite | Resultado |
|---|---|
| `npx vitest run __tests__/api/pentest/physical-device-service.test.ts __tests__/api/pentest/electron-hooks-status.test.ts` | **11/11 passed** (worktree `.tmp/worktrees/194` @ `a4e0ade87`) |
| E2E mock-LLM | N/A — sem mapping novo em `test-mapping.json` para physical-device; escopo unitário suficiente para AC |
| `npm run lint` / `npm test` full | Não reexecutados neste gate (escopo pedido: physical-device + related) |

## Residuais (não bloqueiam)

1. Sem teste de componente React dedicado para o empty `physical-device-unavailable` (AC-194-1 UI coberto por inspeção + data-testid).
2. Teste AC-194-5 do mock é fraco isoladamente; contrato tipado + grep de produção fecham o AC.
3. Espelho scrcpy host permanece stretch/MVP status-only (documentado na UI i18n) — alinhado à spec.

## Ação requerida

Nenhuma para merge pelo eixo QA. Tech Lead: despachar AppSec no tip `a4e0ade87`.
