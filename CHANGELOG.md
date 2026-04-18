# Changelog

All notable changes to this project are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub Actions CI workflow running `pytest` on push and pull request.
- `CONTRIBUTING.md` with branching strategy, Conventional Commits guide, and release process.
- `CODEOWNERS` mapping the repository to `@GreyFlames07` for review enforcement.
- Pull request template and bug / feature issue templates under `.github/`.
- `SECURITY.md` with vulnerability reporting process.
- `.editorconfig` preserving trailing whitespace in Markdown files.

### Changed

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

[Unreleased]: https://github.com/GreyFlames07/forge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/GreyFlames07/forge/releases/tag/v0.1.0
