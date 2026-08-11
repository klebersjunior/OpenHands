# Spec Técnica — PROJETOSIN-200: All-in-one Findings + Engagement Manager

**ADR:** [0001 — Plataforma de Pentest com IA](../../adrs/0001-plataforma-pentest-ia-extensao-openhands.md) (accepted) — sem nova ADR.
**Card Plane:** PROJETOSIN-200 — `5b14df7f-a052-4589-8a79-90fd3e69bfe1`
**Épico:** PROJETOSIN-181
**Prioridade:** P1 — bloqueia smoke PO da release Fases 0–4
**Agente:** Tech Lead (spec + implementação no mesmo checkout; escritor único)

---

## Problema

O `docker compose` all-in-one sobe só `agent-canvas`. A UI chama `GET /api/pentest/me/capabilities`. O entrypoint encaminha `/api` ao agent-server, que responde 404. O client trata 404 como capabilities vazias e o `CapabilityGate` esconde o card Pentest.

`npm run dev` já registra prefixos longos (`/api/pentest/me`, `/api/pentest/findings` → :18002; `/api/pentest/engagements` → :18003) mas **não** sobe os processos. Os fragments existem e nunca foram incluídos:

- `services/findings-service/docker-compose.fragment.yml`
- `services/engagement-manager/docker-compose.fragment.yml`

Findings continua **master**; DefectDojo continua **espelho** (ADR-0001). Sem mudança de RBAC.

---

## Decisão de desenho: (B) containers irmãos + Docker DNS

| Opção | O quê | Por que não / sim |
|-------|--------|-------------------|
| **(A)** sidecars no image all-in-one | uvicorn Findings/EngMgr + Postgres **dentro** de `agent-canvas` | Infla a imagem; dois Postgres no mesmo PID namespace; fragments e Dockerfiles já existem como serviços | 
| **(B)** irmãos no compose + rotas via DNS | `findings-service:8000` / `engagement-manager:8000` na rede do projeto | **Escolhida.** Reusa fragments; Postgres fica nos containers `postgres:16-alpine`; `docker compose up` não exige rebuild da imagem all-in-one para adicionar DB |

`127.0.0.1:18002` **dentro** de `agent-canvas` não alcança um irmão. O entrypoint deve usar hostname Docker, não loopback.

Upstreams injetados no `agent-canvas` (defaults para `docker compose up` funcionar sem flags extras):

| Env | Default |
|-----|---------|
| `FINDINGS_UPSTREAM` | `http://findings-service:8000` |
| `ENGMGR_UPSTREAM` | `http://engagement-manager:8000` |

Comando smoke: `HOST_PORT=9000 docker compose up -d` (include no `docker-compose.yml` raiz — sem `-f` extra).

---

## Contratos

### Ingress (`docker/entrypoint.sh`)

Prefixos **mais longos antes** de `/api=agent-server` (longest-prefix já é o contrato de `scripts/ingress.mjs` / `static-server.mjs`):

| Prefixo | Upstream |
|---------|----------|
| `/api/pentest/me` | `$FINDINGS_UPSTREAM` |
| `/api/pentest/findings` | `$FINDINGS_UPSTREAM` |
| `/api/pentest/engagements` | `$ENGMGR_UPSTREAM` |
| `/api/automation` | `127.0.0.1:$AUTOMATION_PORT` (inalterado) |
| `/api` | `127.0.0.1:$AGENT_SERVER_PORT` (inalterado) |

Aplicar nos três blocos de rotas: ingress backend-only, static-server full, static-server public-mode.

### Auth

- Uma única session key para canvas + Findings + EngMgr.
- Compose: `SESSION_API_KEY` **ou** `LOCAL_BACKEND_API_KEY` (fallback). Repassar aos três como `SESSION_API_KEY` / `LOCAL_BACKEND_API_KEY` / `OH_SESSION_API_KEYS_0`.
- Header: `X-Session-API-Key` (já usado pelo FE e pelo `shared.auth_middleware`).
- `DEFAULT_PENTEST_PROFILE=pentester` (já é o default do middleware — manter explícito no compose para smoke).
- Sem senha/DB/token hardcoded no git. `FINDINGS_DB_PASSWORD` e `ENGMGR_DB_PASSWORD` obrigatórios via `.env` (fragments já usam `:?required`).

### UI (sem mudança de semântica do gate)

- `CapabilityGate` **não muda**.
- `PentestService.getMyCapabilities()` já fail-fecha em 401/403/404. Estender para **502/503** (upstream irmão down → proxy 502) para não disparar toast do QueryCache. Mesmo contrato visual: `{ profile: null, capabilities: [] }`.

### Compose

`docker-compose.yml` inclui os dois fragments. `agent-canvas` recebe os upstreams e `depends_on` (health) dos dois apps.

Rede: default do projeto Compose. Sem overlay extra.

---

## Segurança

- Não commitar `.env`. Placeholders só em `.env.sample` e `docker/compose.env.example`.
- `dev-session-key` continua proibido sem `PENTEST_ALLOW_DEV_SESSION_KEY=1`.
- Portas 18002/18003 dos fragments permanecem publicadas (debug local). Superfície aceitável no desktop do pentester; o smoke usa só `HOST_PORT`.
- EngMgr continua com Docker socket (já na spec 185) — não ampliar.
- DefectDojo: só env de espelho; não provisionar DD novo.

---

## Fora de escopo

Nova ADR, farm mobile, iOS, K8s, Ollama, mapa RBAC, subir Findings/EngMgr em `npm run dev`, mudar `CapabilityGate`.

---

## Critérios de aceite

1. **AC-200-1:** Com `.env` contendo `SESSION_API_KEY` (ou `LOCAL_BACKEND_API_KEY`) + senhas de DB, `HOST_PORT=9000 docker compose up -d` → `GET http://127.0.0.1:9000/api/pentest/me/capabilities` com `X-Session-API-Key` igual à key = **200** e `pentest.workspace.create` no array.
2. **AC-200-2:** Home / seletor de workspace mostra o card **Pentest**.
3. **AC-200-3:** Findings down → UI fail-closed (sem card), **sem toast**.
4. **AC-200-4:** Nenhum password/secret de DB hardcoded no repo.
5. **AC-200-5:** `.env.sample`, `docker/compose.env.example` e smoke em `docs/releases/2026-08-11-plataforma-pentest-fases-0-4.md` atualizados.

---

## Verificação local (porta 9000)

```powershell
# .env (não commitar) — gerar valores; não usar dev-session-key
# SESSION_API_KEY=<64 hex>
# FINDINGS_DB_PASSWORD=<random>
# ENGMGR_DB_PASSWORD=<random>
# LOCAL_BACKEND_API_KEY deve ser igual a SESSION_API_KEY (ou omitir e deixar o compose copiar)

$env:HOST_PORT = "9000"
$env:AGENT_CANVAS_IMAGE = "agent-canvas:local"
docker compose up --build -d

$key = (Select-String -Path .env -Pattern '^SESSION_API_KEY=').Line.Split('=',2)[1]
curl.exe -s -H "X-Session-API-Key: $key" "http://127.0.0.1:9000/api/pentest/me/capabilities"
# Esperado: {"profile":"pentester","capabilities":[...,"pentest.workspace.create",...]}

# Browser: http://127.0.0.1:9000/canvas/
```

Rebuild da imagem `agent-canvas` é necessário **uma vez** após a mudança do `entrypoint.sh`. O `docker compose build` em andamento no host **não** deve ser morto; o próximo `up --build` pega o entrypoint novo.

---

## Dependências

- Reusa PROJETOSIN-182 (capabilities), 184 (Findings), 185 (EngMgr).
- Não bloqueia nem reabre ADR-0001.
