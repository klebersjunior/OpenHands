# Specs ÔÇö Fase 3 Electron + device f├¡sico + autonomia UI (PROJETOSIN-181)

**ADR:** [0001](../../adrs/0001-plataforma-pentest-ia-extensao-openhands.md) (accepted)  
**Blueprint:** ┬º4.2 Electron ┬À ┬º5.4 autonomia ┬À ┬º6.4 device f├¡sico ÔÇö [blueprint](../../product/blueprint-plataforma-pentest-ia.md)  
**Base git:** fork `klebersjunior/OpenHands` tip `4eb43759b` (Fases 0ÔÇô2 Done)

## Fora de escopo (Fase 3)

- Farm Corellium / Genymotion
- IPA / iOS
- Fase 4 orquestra├º├úo avan├ºada (multi-agent playbooks, farm remoto)

## Cards

| Card | Spec | Branch | Worktree | Agente(s) |
|------|------|--------|----------|-----------|
| PROJETOSIN-193 | [193-electron-docker-adb-ipc.md](./193-electron-docker-adb-ipc.md) | `feat/fase3-electron-ipc-193` | `.tmp/worktrees/193` | devops (lead) ÔåÆ backend |
| PROJETOSIN-194 | [194-physical-android-device.md](./194-physical-android-device.md) | `feat/fase3-physical-device-194` | `.tmp/worktrees/194` | backend ÔåÆ frontend (ap├│s contrato IPC 193) |
| PROJETOSIN-195 | [195-autonomy-modes-ui.md](./195-autonomy-modes-ui.md) ┬À [195-design-notes.md](./195-design-notes.md) | `feat/fase3-autonomy-ui-195` | `.tmp/worktrees/195` | design ÔåÆ frontend |

## Paralelismo

```
193 DevOps (IPC foundation) ÔöÇÔöÇÔû║ 193 Backend (bridge/allowlist helpers)
         Ôöé
         ÔööÔöÇÔöÇ contrato est├ível ÔöÇÔöÇÔû║ 194 (device f├¡sico + reconnect)
195 Design (autonomia UI) ÔöÇÔöÇÔû║ 195 Frontend
```

- **Paralelo agora:** 193 (worktree isolada) ┬À Design-195 (worktree isolada).
- **194:** come├ºa implementa├º├úo ap├│s handlers `adb:*` de 193 est├íveis no PR/branch; stubs/contratos podem espelhar esta pasta de specs.
- **Frontend-195:** s├│ ap├│s `195-design-notes.md` no worktree 195.
- PRs **somente** no fork `klebersjunior/OpenHands`. Gates: **AppSec cr├¡tico em 193** ÔåÆ Design (195) ÔåÆ QA ÔåÆ AppSec; **sem auto-assinatura**.

## Depend├¬ncias cruzadas

```
ADR-0001 notes 1ÔÇô3 ÔöÇÔöÇÔû║ 193 IPC docker:compose:* + adb:*
Emulator UI Fase 2 (main) ÔöÇÔöÇÔû║ 194 reusa aba Emulador / status patterns
EngMgr autonomy_mode + PENTEST_AUTONOMY_MODE (187 AppSec) ÔöÇÔöÇÔû║ 195 UI + propagate env
```

## Seguran├ºa (lembrete global)

- Autonomia **server-side only** via `PENTEST_AUTONOMY_MODE` ÔÇö **nunca** confiar `autonomy_mode` em args MCP do cliente/agente.
- Hooks Electron **s├│** com `PENTEST_ELECTRON_HOOKS_ENABLED=true` no modo local; modo servidor ÔåÆ desabilitados (403 / unavailable).
- IPC: allowlist de comandos/args; sem shell arbitr├írio; sem path traversal em compose files.

## CI (contexto)

- Polyfill `ProgressEvent` / ubuntu Test ÔÇö j├í conhecido.
- mock-llm teste 124 flaky residual ÔÇö n├úo bloquear merge Fase 3 se flaky isolado documentado.
