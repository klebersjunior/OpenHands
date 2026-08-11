# services/shared

Middleware e utilitários Python compartilhados entre `findings-service`,
`engagement-manager` e (via PYTHONPATH) MCP servers.

## Módulos

| Arquivo | Card | Papel |
|---------|------|-------|
| `auth_middleware.py` | 182 | `X-Session-API-Key` + capabilities |
| `capabilities.py` | 182 | `PROFILE_CAPABILITIES` (espelho TS) |
| `otel_setup.py` | 199 | TracerProvider + OTLP (no-op sem endpoint) |
| `redaction.py` | 199 | Scrub de secrets em attrs/metadata |
| `custody.py` | 199 | Hash-chain helpers (SHA-256) |

## Observabilidade (PROJETOSIN-199)

```python
from shared.otel_setup import setup_otel, emit_finding_mutate

setup_otel("findings-service")  # lifespan
emit_finding_mutate(action="create", finding_id=..., engagement_id=...)
```

Vars: `OTEL_EXPORTER_OTLP_ENDPOINT`, `PENTEST_OTEL_ENABLED`,
`PENTEST_OTEL_LLM_BODIES` (default false). Ver `.env.sample` e
`config/defaults.json` → `pentest.otel`.
