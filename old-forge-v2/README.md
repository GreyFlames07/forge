# Forge V2

Forge V2 is a schema runtime, workbench CLI, and skill/framework system for building software vertically while preserving a working bootstrap path throughout the build.

## What is in this repo

- `docs/forge-v2-schema.md` — the V2 schema contract
- `docs/forge-v2-architecture.md` — the V2 architecture and workbench model
- `frameworks/` — stage framework definitions
- `skills/` — skill source files
- `.agents/skills/` — installable agent skill folders
- `src/cli/` — the Forge V2 CLI

## Local development

```bash
uv venv --python 3.13 .venv
uv pip install -e . pytest
.venv/bin/pytest -q
```

## Install the CLI and skills locally

```bash
./scripts/install-skills.sh install
```

This links the packaged Forge skills into:

- `~/.claude/skills` for Claude Code
- `~/.codex/skills` for Codex
- `~/.agents/skills` for agentskills.io-compatible clients such as VS Code Copilot and Cursor
- `~/.copilot/skills` as an additional Copilot-local target when `~/.copilot/` already exists

## Build distributions

```bash
uv build
```

This produces:

- `dist/*.tar.gz`
- `dist/*.whl`

## Release model

- CI runs tests and a smoke build on `main` pushes and PRs
- tagged releases `v*.*.*` build sdist and wheel
- release workflow publishes artifacts to GitHub Releases and PyPI

## Quick smoke test

```bash
./.venv/bin/forge init --root /tmp/forge-smoke --profile cli-tool --name "Smoke" --id smoke
./.venv/bin/forge list --forge-dir /tmp/forge-smoke/forge
./.venv/bin/forge context core --forge-dir /tmp/forge-smoke/forge
./.venv/bin/forge graph --forge-dir /tmp/forge-smoke/forge --no-open
```

`forge init` vendors the Forge docs, frameworks, and project-local `.agents/skills/` into the initialized directory, then symlinks those project-local skills into the home scan directories above unless you pass `--no-vendor-assets` or `--no-link-skills`.

## Public CLI vs workbench

The public CLI is intentionally small:

- `forge init`
- `forge list`
- `forge context`
- `forge graph`

`forge/workbench/` remains part of the framework, but it is an internal artifact model used by the stage skills. It stores build-planning and validation state for agent workflows; it is not a separate public command surface.
