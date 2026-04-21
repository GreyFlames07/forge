# Changelog

All notable changes to this project are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] — 2026-04-21

### Fixed

- Pip-installed Forge CLI now resolves the renamed `ai-forge-cli` distribution before legacy package names when computing `forge --version` and when bootstrapping init/update assets. This prevents stale `0.1.1` version output and ensures the matching installed release bundle is fetched, including `forge-compose`.
- `forge-implement` SKILL.md: clarified that `forge-test-writer` and `forge-implementer` are skills, not Task `subagent_type` values. Orchestrators must spawn `subagent_type: "general-purpose"` and invoke the skill by name in the prompt. Also documents that subagents inherit no env (no `$FORGE_SPEC_DIR`, no CWD) — prompts must pass the absolute spec-dir path explicitly.
- `FORGE_SPEC_DIR` export in README quick-start and `forge init` output now wraps the path in double quotes so it is valid for directories containing spaces.
- `forge init`/`forge update` now work from pip-installed distributions by bootstrapping bundled skill/template assets from the matching tagged GitHub source archive when repo-local assets are unavailable.

### Added (post 0.1.0)

- `forge --version` global CLI flag to print the installed package version.
- GitHub Actions release workflow (`.github/workflows/release.yml`) that runs on `v*.*.*` tags, validates tag/version alignment, builds wheel+sdist, creates a GitHub Release with artifacts, and publishes to PyPI via trusted publishing.
- L5.4 `observability` block integrated into `L5_operations.yaml` (not a new file): per-module SLA defaults with per-atom overrides, Prometheus metric declarations (counter/gauge/histogram/summary), trace sample rates, PromQL alert rules with severity and evaluation window. Schema (validation rules 13–21), authoring guide (Section 4), and example corpus (`PAY` + `USR` modules) all updated.
- `forge-validate` Phase 4: reads `observability` from L5, asserts live probe latencies against resolved SLA, checks `/metrics` endpoint for declared metric presence, and validates alert PromQL syntax. New `--skip-observability` flag. Report summary table gains an Observability row.
- Batching refactor across all interviewing skills: `forge-discover`, `forge-atom`, and `forge-decompose` non-negotiable #1 updated from "one concept per turn" to "batch within sub-phases, sequence across them". Sub-phase question sequences reorganised into explicit batches where questions are independent of each other.

- `forge-validate` skill: post-implementation validator that checks source code against L3 spec contracts (static analysis), maps test suite results back to spec elements (test mapping), and fires synthetic live probes against the running system with exact contract assertion, LLM-reasoned behavioral assertion, and log-verified side effect checking. Produces `validation-report.md` in the spec dir.
- `docs/skills/forge-validate/framework.md`: full mental model covering phase mechanics, probe construction, exact vs behavioral assertion, side effect verification, and CI usage.

### Added

- `forge-armour`, a post-`forge-audit` security hardening skill that captures the project trust model, runs an 8-pass security review, proposes project/module/atom-level spec hardening, and only writes approved changes.
- `forge-armour` templates for `security-profile.md`, `armour-YYYY-MM-DD.md`, and `armour-history.md`.
- Framework documentation for `forge-armour` under `docs/skills/forge-armour/framework.md`.
- GitHub Actions CI workflow running `pytest` on push and pull request.
- `CONTRIBUTING.md` with branching strategy, Conventional Commits guide, and release process.
- `CODEOWNERS` mapping the repository to `@GreyFlames07` for review enforcement.
- Pull request template and bug / feature issue templates under `.github/`.
- `SECURITY.md` with vulnerability reporting process.
- `.editorconfig` preserving trailing whitespace in Markdown files.

### Changed

- README, install flow, and `forge init` output now include `forge-armour` as the recommended post-audit security hardening pass before implementation.
- README rewritten in forge visual style with ASCII banner, pipeline diagram, and tables.
- Branch protection enabled on `main`: requires pull request, code-owner review, linear history. Admin bypass retained for solo-maintainer flows.

## [0.1.0] — 2026-04-18

### Added

- Initial release.
- Six-layer YAML spec system (L0 Registry through L5 Operations) with schema docs and an example corpus.
- Python CLI (`forge`) with five commands: `init`, `context`, `list`, `inspect`, `find`.
- Seven agent skills: `forge-discover`, `forge-decompose`, `forge-atom`, `forge-audit`, `forge-implement` plus the two subagent skills `forge-test-writer` and `forge-implementer`.
- Animated init banner with `.forge/` project layout and schema-template symlinks.
- Skill installation script (`scripts/install-skills.sh`) covering Claude Code, OpenAI Codex CLI, and agentskills.io-compatible clients (VS Code Copilot, Cursor).
- 49 pytest test cases across CLI, index, walker, find, and init command.
- Full framework documentation for each skill under `docs/skills/<name>/framework.md`.

[Unreleased]: https://github.com/GreyFlames07/forge/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/GreyFlames07/forge/releases/tag/v0.1.3
[0.1.0]: https://github.com/GreyFlames07/forge/releases/tag/v0.1.0
