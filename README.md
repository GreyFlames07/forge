# forge

Spec-driven agent development. A six-layer YAML spec system (L0–L5), a Python CLI for context assembly, and a pipeline of seven agentic skills that take a human from a vague product idea to working, audited, implementable code — with the agent driving the interview.

## What it does

1. **`forge-discover`** — interviews the human to turn a product idea into a project foundation (modules, L0 vocabulary, L1 conventions, L5 runtime posture).
2. **`forge-decompose`** — breaks each module into an exhaustive, classified list of atom stubs via a four-pass extraction.
3. **`forge-atom`** — fills each atom stub with a full L3 spec through one of three interview shapes (draft-then-review / example-driven / structured deep-dive), with reuse-before-create probes and cross-system consistency checks.
4. **`forge-audit`** — quality-gates the completed spec corpus across seven audit passes (completeness, consistency, L0 hygiene, reachability, risk, policy coverage) with severity escalation for persistent findings.
5. **`forge-implement`** — orchestrates code + test generation from audited specs, delegating to two subagent skills (`forge-test-writer`, `forge-implementer`) in strict test-before-implementation isolation. Dependency-graph-driven parallelism, retry-with-spec-linked-feedback, `.forge/` project layout.

The CLI (`forge` command) provides context assembly primitives (`list`, `inspect`, `context`, `find`) that the skills rely on.

## Install from GitHub

### Fresh machine — one-time setup

```bash
# 1. Clone
git clone https://github.com/WillDefina/forge.git
cd forge

# 2. Create a venv + install the CLI
uv venv --python 3.13 .venv
uv pip install -e . pytest

# 3. Wire up skills globally (Claude Code, Codex, agentskills.io clients)
./scripts/install-skills.sh install
```

Verify:
```bash
forge --help        # shows: init, context, list, inspect, find
.venv/bin/pytest    # should report 49 passed
```

If `forge: command not found`, add `~/.local/bin` to your shell PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Requirements

- Python ≥ 3.13 (or adjust `pyproject.toml`)
- `uv` (recommended) or `pip`
- At least one agent client installed: Claude Code, OpenAI Codex CLI, or any agentskills.io-compatible client (VS Code Copilot, Cursor)

## Quick start

### Initialize a new project

```bash
mkdir ~/my-idea && cd ~/my-idea
forge init
```

This creates:
- `.forge/` — spec directory with L-layer subdirs + 12 schema templates symlinked
- `.claude/skills/`, `.codex/skills/`, `.agents/skills/` — skill symlinks for every supported client (7 skills each, 21 symlinks total)

### Start an agent session

```bash
cd ~/my-idea
claude   # or: codex
```

Trigger a forge skill with natural language:

```
I want to build a tool that helps accountants close the books faster.
```

`forge-discover` activates and walks you through product workshopping → module boundaries → L0 vocabulary → L1 conventions → L5 runtime posture. All output writes to `.forge/`.

Claude Code also supports slash shortcuts:
```
/forge-discover  /forge-decompose  /forge-atom  /forge-audit  /forge-implement
```

## CLI reference

```
forge init                          # scaffold a new project in cwd
forge list [--kind <kind>]          # enumerate entities in the spec dir
forge inspect <id>                  # lightweight metadata probe
forge context <id>                  # full implementation-ready bundle
forge find <query> [--kind]         # search by name or description
```

Spec-dir resolution: `--spec-dir` > `$FORGE_SPEC_DIR` > auto-discover (walks upward for `.forge/` or legacy `forge/docs/`).

## Repository layout

```
forge/
├── src/
│   ├── cli/                    # CLI package (forge command)
│   ├── templates/              # L0-L5 schema templates (referenced by forge init)
│   └── example/                # Working example spec corpus (used by tests)
├── .agents/skills/             # The 7 forge skills (installed into agent clients)
│   ├── forge-discover/
│   ├── forge-decompose/
│   ├── forge-atom/
│   ├── forge-audit/
│   ├── forge-implement/
│   ├── forge-test-writer/       # Subagent, dispatched by forge-implement
│   └── forge-implementer/       # Subagent, dispatched by forge-implement
├── docs/
│   ├── skills/                  # Human-facing framework docs for each skill
│   └── cli-guide.md             # Full CLI reference
├── scripts/
│   └── install-skills.sh        # Global skill install + CLI symlink
├── tests/                       # pytest suite (49 tests)
└── pyproject.toml
```

## Framework

Six-layer spec system:

- **L0 Registry** — vocabulary (types, errors, constants, external schemas, side-effect markers)
- **L1 Conventions** — project-wide defaults (retry policy, log format, security posture, verification floors)
- **L2 Architecture** — modules (ownership boundaries, tech stacks, persistence, access permissions, policies)
- **L3 Behavior** — atoms (smallest unit of specified behavior) and artifacts (non-executing dependencies)
- **L4 Composition** — flows (saga orchestrations) and journeys (user-facing multi-step paths)
- **L5 Operations** — runtime posture (platform, deployment, rate limits, event semantics)

Each layer is a source-of-truth YAML file set. The CLI walks the reference graph; the skills produce and consume these files.

See `docs/framework-overview.md` for the full schema reference.

## Uninstall

```bash
cd forge
./scripts/install-skills.sh uninstall
# Optionally delete the repo clone
```

## Testing locally

The example spec corpus at `src/example/` is a complete working system (fictional payments app) used by the test suite and serves as reference.

```bash
.venv/bin/pytest -v                           # run the 49-test suite
export FORGE_SPEC_DIR="$(pwd)/src/example"
forge list                                    # explore the example
forge context atm.pay.charge_card             # see a full atom bundle
```

## Adding a new skill

Skills are markdown files following the [agentskills.io](https://agentskills.io) spec. To add one:

1. Create `.agents/skills/<name>/SKILL.md` with frontmatter (`name`, `description`).
2. Add the skill name to `SKILLS=()` in `scripts/install-skills.sh`.
3. Add the skill name to `SKILL_NAMES` in `src/cli/commands/init.py`.
4. Re-run `./scripts/install-skills.sh install` and `forge init --force` in existing projects.

## License

See `LICENSE` (add one if you haven't — MIT is a reasonable default for dev tools).
