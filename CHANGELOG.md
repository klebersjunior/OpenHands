# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Plataforma de Pentest com IA (ADR-0001) — Fases 0–4 no fork interno Heimdall:
  engagement isolado, MCP ofensivos (recon/webscan/sast/mobile/network/engine),
  Findings Service + espelho DefectDojo, emulador/MobSF, Electron IPC + device físico,
  UI de autonomia, orquestrador de playbooks, OTEL/SigNoz + chain of custody.
- Release notes: `docs/releases/2026-08-11-plataforma-pentest-fases-0-4.md`
- All-in-one compose inclui Findings + Engagement Manager (PROJETOSIN-200);
  ingress Docker roteia `/api/pentest/*` aos irmãos via Docker DNS.
- Aba **Pentest** no painel direito (só em workspace pentest): checklist OWASP WSTG
  com acionamento das tools MCP do blueprint por etapa (PROJETOSIN-203).
- Skills de **Segurança da Informação** no catálogo (playbook, recon, web, rede,
  mobile, findings → engagement) — PROJETOSIN-204.
- Ativos de pentest (IP/hostname/domínio/URL/e-mail) na criação, edição e aba
  Pentest; allowlist gravada em `.openhands/SCOPE.md`; MCP pentest
  (incl. mcp-findings) anexados à conversa — PROJETOSIN-205.
- Gestão de usuários em tabela (grupo + permissões) e grupos customizáveis
  no login interno (`/settings/users`) — PROJETOSIN-206.
- Emulador Android budtmo (`budtmo/docker-android:emulator_13.0`) no compose
  all-in-one via `COMPOSE_PROFILES=android-emulator`; ADB `:5555`, noVNC `:6080`
  e `EMULATOR_NOVNC_URL` no agent-canvas / mcp-mobile.
- Runtimes ofensivos web/network/sast no compose all-in-one via
  `COMPOSE_PROFILES=pentest-runtimes` (ZAP `:8080`, nmap/msfrpcd, Semgrep/Trivy).

## [1.0.0-alpha.2] - 2025-05-11

### Added

- Initial npm package release of `@openhands/agent-canvas`
- CLI entry point (`npx @openhands/agent-canvas`) to run full stack locally
- Library build mode with component barrel exports
- Subpath exports for modular imports:
  - `@openhands/agent-canvas/browser`
  - `@openhands/agent-canvas/conversation`
  - `@openhands/agent-canvas/files`
  - `@openhands/agent-canvas/settings`
  - `@openhands/agent-canvas/sidebar`
  - `@openhands/agent-canvas/terminal`
  - `@openhands/agent-canvas/i18n`
- TypeScript type declarations
- GitHub Actions workflow for automated npm publishing (OIDC trusted publishing)

[Unreleased]: https://github.com/OpenHands/agent-canvas/compare/v1.0.0-alpha.2...HEAD
[1.0.0-alpha.2]: https://github.com/OpenHands/agent-canvas/releases/tag/v1.0.0-alpha.2
