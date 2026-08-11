# Microagents / skill packs (PROJETOSIN-196)

Domain prompt suffixes and tool allowlists for orchestration playbooks.

## Wiring

1. On `POST …/orchestration/runs` the runner records `playbook_id` + `domain`.
2. Conversation / agent context should attach the matching suffix from this folder
   (or the skill id listed below) — UI selects playbook only; no new Agent Server fork.
3. Tool allowlist by domain (enforced conceptually for MCP attach; orchestrator
   only invokes `engine_*` + domain tools declared on the playbook phase):

| Domain | Allowlist | Suffix file | Suggested skill id |
|--------|-----------|-------------|--------------------|
| web | recon + webscan + engine | `web.md` | `pentest-web-orchestrator` |
| network | network + engine | `network.md` | `pentest-network-orchestrator` |
| mobile | mobile + engine | `mobile.md` | `pentest-mobile-orchestrator` |

Frontend (AC-196-6) may surface playbook selection only; skill activation can
reuse existing skills UI once packs are copied under `.openhands/skills/`.
