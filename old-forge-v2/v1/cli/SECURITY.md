# Security policy

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities.

Instead:

1. Use GitHub's [private vulnerability reporting](https://github.com/GreyFlames07/forge/security/advisories/new) to open an advisory draft visible only to maintainers.
2. Provide: affected version / commit, reproduction steps, impact assessment, and any mitigation ideas.
3. Expect an acknowledgement within a week. Triage and fix timelines depend on severity.

## Scope

In scope:

- The `forge` CLI package.
- Agent skill files (`SKILL.md`, framework docs) — including prompt-injection vectors or confused-deputy issues.
- Install scripts (`scripts/install-skills.sh`).
- Example spec corpus — misleading content that could lead agents to produce insecure code.

Out of scope:

- Third-party agent clients (Claude Code, Codex, Copilot) — report to those projects directly.
- The `uv` / `pip` / Python toolchain — upstream.
- Specs or code YOU produce using forge — that's your project's concern, not forge's.

## Disclosure

After a fix is available and an affected release is published, the advisory is disclosed publicly with credit to the reporter (unless anonymity is requested).
