# Spec T├®cnica ÔÇö PROJETOSIN-195: UI modos de autonomia (Manual / Semi / Aut├┤nomo)

**ADR:** docs/adrs/0001-plataforma-pentest-ia-extensao-openhands.md (accepted) ÔÇö autonomia ┬À Blueprint ┬º5.4  
**Card Plane:** PROJETOSIN-195 ÔÇö `8ba3955a-4268-4d85-88ea-b7d481039ab2`  
**Agentes:** design (antes) ÔåÆ frontend (+ backend m├¡nimo EngMgr/propagate se faltar)  
**Prioridade:** P1  
**Base git:** `4eb43759b`  
**Branch:** `feat/fase3-autonomy-ui-195`  
**Worktree:** `.tmp/worktrees/195`  
**PR target:** fork `klebersjunior/OpenHands` only

---

## Objetivo

Seletor de **modo de autonomia** na UI (engagement / sess├úo pentest), alinhado ao blueprint:

| Modo | Valor can├┤nico | Comportamento (j├í no server) |
|---|---|---|
| Manual / Copiloto | `manual` | Toda tool intrusiva (e MVP: gate amplo) exige confirma├º├úo |
| Semi-aut├┤nomo (**padr├úo**) | `semi_autonomous` | Recon/passivo livre; ativas com confirmation gate |
| Aut├┤nomo | `autonomous` | Sem gate (exceto pol├¡tica max-risk futura); allowlist inviol├ível |

A UI **persiste** a escolha no Engagement Manager e garante que o runtime MCP recebe `PENTEST_AUTONOMY_MODE` ÔÇö **nunca** via argumento de tool MCP.

---

## Seguran├ºa (n├úo negoci├ível ÔÇö fix 187)

1. Source of truth runtime: env `PENTEST_AUTONOMY_MODE` lido por `services/mcp-servers/shared/confirmation.py::get_autonomy_mode()`.  
2. Schemas MCP **n├úo** exp├Áem `autonomy_mode`.  
3. UI/API EngMgr podem enviar `autonomy_mode` no **CRUD do engagement** (humano autenticado + session key) ÔÇö isso **n├úo** ├® o agente MCP.  
4. Mudan├ºa de modo ÔåÆ atualizar env dos containers MCP/runtime do engagement (recreate ou restart service com novo env). Se restart completo for pesado no MVP: documentar ÔÇ£aplica na pr├│xima provision/restartÔÇØ **e** preferir PATCH que dispara reload do env no compose project.  
5. Modo `autonomous` gated por capability RBAC (ex. `pentest.autonomy.autonomous` / perfil admin) ÔÇö usu├írios sem capability veem op├º├úo disabled + tooltip.

---

## Ordem de trabalho

1. **Design** ÔÇö `docs/specs/fase-3/195-design-notes.md` no worktree 195: coloca├º├úo do seletor, copy, estados, a11y, RBAC disabled.  
2. **Frontend** ÔÇö implementar conforme design + esta spec.  
3. **Backend** (se necess├írio no mesmo PR): endpoint PATCH engagement j├í existe parcialmente ÔÇö completar propagate env.  
4. Gates: Design (UI) ÔåÆ QA ÔåÆ AppSec.

---

## Contratos

### Tipos (j├í existem)

`src/types/workspace-types.ts`:

```ts
export type AutonomyMode = "manual" | "semi_autonomous" | "autonomous";
```

Reutilizar; n├úo criar union paralela.

### Engagement Manager

| Op | Uso |
|---|---|
| `POST /engagements` | `autonomy_mode` default `semi_autonomous` (j├í) |
| `PATCH /engagements/{id}` | body `{ autonomy_mode }` ÔÇö garantir schema Update + service |
| `GET /engagements/{id}` | retorna modo atual |

Ap├│s PATCH bem-sucedido, EngMgr deve:

1. Persistir DB  
2. Best-effort: atualizar env `PENTEST_AUTONOMY_MODE` no project compose do engagement (runtime + mcp sidecars se aplic├ível)  
3. Resposta inclui `autonomy_mode` efetivo + `propagation: "applied" | "pending_restart" | "n/a"`

Client frontend: `src/api/pentest/engagement-service.ts` (estender se j├í houver de 185/183).

### Conversation metadata

J├í h├í `autonomy_mode` em `PentestConversationMetadata` / `use-create-conversation`. Manter sincronizado:

- Cria├º├úo workspace pentest: envia modo escolhido  
- Troca mid-session: PATCH engagement + atualizar metadata local; **n├úo** patchar settings LLM com autonomy fake

### Confirmation UI (m├¡nimo)

Gate `confirmation_required` j├í existe server-side. MVP 195:

- Seletor de modo + persist├¬ncia + propagate  
- Superf├¡cie de ÔÇ£Approve toolÔÇØ pode permanecer stub se 187 ainda stub ÔÇö **n├úo** expandir Fase 4; se j├í houver toast/error no chat para `confirmation_required`, apenas garantir copy i18n coerente com o modo Manual/Semi

---

## UI ÔÇö requisitos para Design

**Design notes:** [195-design-notes.md](./195-design-notes.md) (can├┤nico para FE).

**Coloca├º├úo (fechada pelo Design):**

1. Fluxo cria├º├úo workspace pentest (`PentestWorkspaceFields`, junto engagement / runtime profile) ÔÇö seletor obrigat├│rio com **default `semi_autonomous`** (corrigir init `manual` herdado de 183)  
2. Header da conversa pentest (chip compacto ao lado do badge) ÔÇö **n├úo** Settings LLM; alterar modo com confirm dialog se mudando **para** Aut├┤nomo (tamb├®m na cria├º├úo ao selecionar Aut├┤nomo)

**Estados:**

- Loading / saving  
- Error propagate (`pending_restart` ÔåÆ banner informativo)  
- Autonomous **sempre vis├¡vel**, `disabled` + tooltip sem capability RBAC (n├úo ocultar via CapabilityGate vazio)  
- Read-only se engagement arquivado (se estado existir)

**a11y:** radiogroup HeroUI/nativo (preferir a chips `aria-pressed`); labels via i18n; foco seguro no dialog de confirma├º├úo (n├úo no bot├úo Confirm).

**Tokens:** HeroUI + `--oh-*`; sem cards decorativos desnecess├írios ÔÇö controle de formul├írio inline.

**Seguran├ºa UX:** helper permanente ÔÇö allowlist de escopo inviol├ível em qualquer modo; Aut├┤nomo gated por RBAC.

i18n prefix sugerido: `PENTEST$AUTONOMY_*` (pode aliasar labels `WORKSPACE_TYPE$AUTONOMY_*` existentes).

### Ajustes UX vs tip pr├®-design (U-1ÔÇªU-6)

Ver ┬º12 de [195-design-notes.md](./195-design-notes.md) ÔÇö default Semi, Aut├┤nomo disabled+tooltip, radiogroup, copy ÔÇ£Manual / CopilotoÔÇØ, coloca├º├úo no header, confirm tamb├®m na cria├º├úo.
---

## AC test├íveis

| ID | Crit├®rio |
|---|---|
| AC-195-1 | Default UI = Semi-aut├┤nomo; valor enviado `semi_autonomous` |
| AC-195-2 | Trocar para Manual ÔåÆ PATCH EngMgr ÔåÆ GET reflete `manual` |
| AC-195-3 | Sem capability autonomous ÔåÆ op├º├úo Aut├┤nomo n├úo selecion├ível |
| AC-195-4 | Vitest: client **n├úo** adiciona `autonomy_mode` a payloads MCP tool |
| AC-195-5 | Com mock EngMgr, banner `pending_restart` quando propagation Ôëá applied |
| AC-195-6 | i18n keys completas (`make-i18n` / check completeness no escopo tocado) |

---

## Gates

| Gate | Foco |
|---|---|
| Design | PASS em notes + review UI |
| QA | AC-195-* |
| AppSec | Confirmar aus├¬ncia de autonomy em schema MCP; PATCH EngMgr authz; autonomous RBAC |

---

## Fora de escopo

- Playbooks multi-agent (Fase 4)  
- Alterar allowlist de escopo  
- Device f├¡sico (194)

---

## Entrega

1. Design notes no worktree ÔåÆ coment├írio Plane  
2. Frontend PR `Plane: PROJETOSIN-195`  
3. N├úo mergear sem Design + QA + AppSec PASS (revisor Ôëá autor)
