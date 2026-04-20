<div align="center">

```
███████╗ ██████╗ ██████╗  ██████╗ ███████╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
█████╗  ██║   ██║██████╔╝██║  ███╗█████╗  
██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  
██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
```

**Spec-driven agent development.**
The agent drives the interview. The specs drive the code.

[![CI](https://github.com/GreyFlames07/forge/actions/workflows/ci.yml/badge.svg)](https://github.com/GreyFlames07/forge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

## What it is

A six-layer YAML spec system, a Python CLI for context assembly, and **nine agent skills** that take a human from a vague product idea to working, audited, hardened, validated code — with the agent asking questions and the human answering, not the reverse.

Built on the premise that **people explain systems well under questioning but poorly when cold-prompted**. forge inverts the default "human prompts agent → agent implements" loop into "agent interviews human → structured spec emerges → agent implements from spec".

Runs in **Claude Code**, **OpenAI Codex CLI**, and any **agentskills.io-compatible client** (VS Code Copilot, Cursor).

---

## The pipeline

```
  idea
    ↓
  forge-discover    →  foundation       (modules, L0 vocab, L1 conventions, L5 posture)
    ↓
  forge-decompose   →  atom inventory   (stub files, module populated, entry-point hints)
    ↓
  forge-atom        →  complete specs   (one atom at a time — three interview shapes)
    ↓
  forge-audit       →  quality gate     (seven audit passes, severity-ranked findings)
    ↓
  forge-armour      →  security hardening (trust model, policies, abuse-case review)
    ↓
  forge-implement   →  code + tests     (parallel subagents, test-before-impl isolation)
    ↓
  forge-validate    →  validation report (static analysis, test mapping, live interaction probes)
    ↓
  working system
```

Each skill is a markdown directive file (agent-facing) plus a longer framework doc (human reference). Each uses the `forge` CLI to sense project state and load context — agents don't inline spec content in prompts.

---

## Install

### Fresh machine — four commands

```bash
git clone https://github.com/GreyFlames07/forge.git
cd forge
uv venv --python 3.13 .venv && uv pip install -e . pytest
./scripts/install-skills.sh install
```

This wires the `forge` binary into `~/.local/bin/` and symlinks the nine skills into `~/.claude/skills/`, `~/.codex/skills/`, and `~/.agents/skills/` — discoverable by every supported client.

### Verify

```
forge --help              # shows: init, context, list, inspect, find
.venv/bin/pytest          # 49 passed
```

### Requirements

| | |
|---|---|
| Python | ≥ 3.13 |
| Package manager | [`uv`](https://docs.astral.sh/uv/) recommended; pip works |
| One agent client | Claude Code, Codex CLI, or an agentskills.io-compatible client |

If `forge: command not found`: add `~/.local/bin` to PATH.

```bash
export PATH="$HOME/.local/bin:$PATH"  # add to ~/.zshrc to persist
```

---

## Quick start

Bootstrap a new project in any empty directory:

```bash
mkdir ~/my-idea && cd ~/my-idea
forge init
```

```
    ✦  INITIALISING FORGE
    ▸ Forge init in /Users/you/my-idea

      ✓ .forge/
      ✓ 6 spec subdirectories
      ✓ 12 schema templates → .forge/templates/
      ✓ 27/27 skill symlinks → .claude/skills/, .codex/skills/, .agents/skills/

    ───── Next steps ─────

      Set the spec dir (add to your shell rc to persist):
        export FORGE_SPEC_DIR="/Users/you/my-idea/.forge"

      Start a session in this directory:
        claude │ codex │ any agentskills.io client

      Trigger a forge skill with a natural-language prompt:
        "I want to build a tool that does X"
        "Decompose the PAY module into atoms"
        "Audit the specs before implementation"
        "Harden the specs for security before implementation"
```

Open an agent session in that directory and describe your idea in natural language. The relevant skill activates; the interview begins.

---

## CLI

| Command | Purpose |
|---|---|
| `forge init` | Scaffold a new project (`.forge/` + skill symlinks + schema templates) |
| `forge update` | Refresh init-managed project assets to the current Forge version |
| `forge list [--kind K]` | Enumerate entities in the spec dir |
| `forge inspect <id>` | Lightweight metadata probe |
| `forge context <id>` | Full implementation-ready bundle for an entity |
| `forge find <query>` | Substring search across names + descriptions |

Spec-dir resolution order: `--spec-dir` flag > `$FORGE_SPEC_DIR` env var > auto-discover (walks upward looking for `.forge/`).

Full CLI guide: [`docs/cli-guide.md`](docs/cli-guide.md).

---

## The nine skills

| Skill | Role | Input | Output |
|---|---|---|---|
| **forge-discover** | Interviewer (product framing) | Vague idea | Project foundation: modules, L0 skeleton, L1 conventions, L5 posture |
| **forge-decompose** | Structural extractor | One bounded module | Exhaustive atom stubs (four-pass extraction) |
| **forge-atom** | Contract specifier | One atom stub | Complete L3 spec + L0 cascades + module completions |
| **forge-audit** | Challenger / reviewer | Completed specs | Severity-ranked findings with inline edits; seven audit passes |
| **forge-armour** | Security challenger | Audited specs | Security hardening pass, trust-model capture, approved project/module/atom security edits |
| **forge-implement** | Orchestrator | Audited spec corpus | Code + tests, dep-graph parallel, test-before-impl isolation |
| **forge-validate** | Post-implementation validator | Implemented system + spec corpus | Validation report: static analysis, test-to-spec mapping, live interaction probes |
| **forge-test-writer** | Subagent | One entity + level | Unit/integration/system tests with audit doc |
| **forge-implementer** | Subagent | One entity | Implementation code, blind to tests |

Skills activate via natural-language prompts (universal) or slash-commands (Claude Code only).

Each skill has a framework doc (mental model) under `docs/skills/<skill>/framework.md` and a directive SKILL.md under `.agents/skills/<skill>/`.

---

## The spec system

Six layers, each a source-of-truth YAML file set.

| Layer | Purpose |
|---|---|
| **L0 Registry** | Vocabulary — types, errors, constants, external schemas, side-effect markers |
| **L1 Conventions** | Project-wide defaults — retry policy, logging, security posture, verification floors |
| **L2 Architecture** | Modules — ownership, tech stacks, persistence, permissions, policies |
| **L3 Behavior** | Atoms (smallest spec unit) + artifacts (non-executing deps) |
| **L4 Composition** | Flows (saga orchestrations) + journeys (user-facing paths) |
| **L5 Operations** | Runtime — platform, deployment, rate limiting, event semantics, observability (SLA targets, metrics, alerts) |

Schema reference: [`docs/framework-overview.md`](docs/framework-overview.md).
Full schema templates: [`src/templates/`](src/templates/).

---

## Repository layout

```
forge/
├── src/
│   ├── cli/              Python CLI package (the forge command)
│   ├── templates/        L0-L5 schema templates (symlinked into projects by forge init)
│   └── example/          Working example spec corpus (used by tests)
├── .agents/skills/       The 9 forge skills (installed into agent clients)
│   ├── forge-discover/
│   ├── forge-decompose/
│   ├── forge-atom/
│   ├── forge-audit/
│   ├── forge-armour/
│   ├── forge-implement/
│   ├── forge-validate/
│   ├── forge-test-writer/
│   └── forge-implementer/
├── docs/
│   ├── skills/           Framework docs for each skill (mental models)
│   ├── cli-guide.md      Full CLI reference
│   └── framework-overview.md
├── scripts/
│   └── install-skills.sh Global skill install + CLI symlink
├── tests/                pytest suite — 49 tests
├── pyproject.toml
└── README.md
```

---

## Development

### Testing

```bash
.venv/bin/pytest -v
```

The `src/example/` directory is a complete working spec corpus (a fictional payments app) that doubles as the test fixture and a reference for what a finished project looks like.

```bash
export FORGE_SPEC_DIR="$(pwd)/src/example"
forge list                              # see what's there
forge context atm.pay.charge_card       # inspect a full atom bundle
forge find charge                       # search across entities
```

### Adding a new skill

1. Create `.agents/skills/<name>/SKILL.md` with [agentskills.io](https://agentskills.io) frontmatter (`name`, `description`).
2. Add the skill to `SKILLS=()` in `scripts/install-skills.sh`.
3. Add the skill to `SKILL_NAMES` in `src/cli/commands/init.py`.
4. Add a framework doc under `docs/skills/<name>/framework.md` if the skill has a substantial mental model.
5. `./scripts/install-skills.sh install` to wire up globally.
6. In any existing projects: `forge update` to refresh their managed scaffolding and local skill links.

### Uninstall

```bash
./scripts/install-skills.sh uninstall
```

Removes all global skill symlinks and the `forge` CLI binary. Does not touch project-local `.forge/` directories (those are owned by each project).

---

## Contributing

Pull requests welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for:

- Branching and commit conventions (Conventional Commits)
- Local dev setup
- PR requirements and CI expectations
- Release process

The repo uses standard open-source governance: no direct pushes to `main`, PRs require code-owner approval, CI must be green, history stays linear.

Changes are tracked in [`CHANGELOG.md`](CHANGELOG.md) following [Keep a Changelog](https://keepachangelog.com).

## Security

Security issues: see [`SECURITY.md`](SECURITY.md). Do not open public issues for vulnerabilities.

## License

MIT — see [`LICENSE`](LICENSE).

---

<div align="center">

<sub>Built for agent-driven development. Questions over prompts. Specs over intentions. Code follows.</sub>

</div>
