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

A hierarchical YAML spec system, a Python CLI for context assembly, and **six agent skills** that take a human from a vague product idea to working, reviewed, and validated code — with the agent asking questions and the human answering, not the reverse.

Built on the premise that **people explain systems well under questioning but poorly when cold-prompted**. Forge inverts the default "human prompts agent → agent implements" loop into "agent interviews human → structured spec emerges → agent implements from spec".

Runs in any agent client that supports skills: **Claude Code**, **OpenAI Codex CLI**, **VS Code Copilot**, **Cursor**, and any other agentskills.io-compatible client.

---

## The pipeline

```
  idea
    ↓
  forge-design    →  system design      (conception, systems, domains, modules, environments)
    ↓
  forge-spec      →  element specs      (elements, properties, operations, types, contracts, flows)
    ↓
  forge-cast      →  repo hydration     (existing codebase → draft Forge spec + uncertainty report)
    ↓
  forge-review    →  quality + security (completeness, consistency, contract correctness, attack vectors)
    ↓
  forge-build     →  code + tests       (parallel subagents, each element gets forge context)
    ↓
  forge-validate  →  validation report  (static analysis, test coverage, behavioral probes)
    ↓
  working system
```

Each skill is a SKILL.md directive (agent-facing) plus a shared `docs/framework-reference.md` (human reference). Agents use the `forge` CLI to load element context — no spec content is inlined in prompts.

---

## Install

### Fresh machine — four commands

```bash
git clone https://github.com/GreyFlames07/forge.git
cd forge
uv venv --python 3.13 .venv && uv pip install -e . pytest
./scripts/install-skills.sh install
```

This wires the `forge` binary into `~/.local/bin/` and symlinks the six skills into `~/.claude/skills/`, `~/.codex/skills/`, and `~/.agents/skills/` — discoverable by every supported client.

### Verify

```
forge --version           # shows installed forge version
forge --help              # shows: init, update, context, list, inspect, find, validate, graph
.venv/bin/pytest          # 74 passed
```

### Requirements

| | |
|---|---|
| Python | ≥ 3.13 |
| Package manager | [`uv`](https://docs.astral.sh/uv/) recommended; pip works |
| Agent client | Claude Code, Codex CLI, or any agentskills.io-compatible client |

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
    ▸ Forge init in /Users/you/my-idea

      ✓ spec/
      ✓ spec/framework.yaml  (framework vocabulary)
      ✓ spec/conception.yaml  (fill in your conception details)

    ───── Next steps ─────

      Edit spec/conception.yaml and replace placeholders:
        id:  <conception>
        name: <ConceptionName>

      Create your first system directory:
        mkdir -p spec/<system>
        touch spec/<system>/system.yaml

      Set the spec dir (add to shell rc to persist):
        export FORGE_SPEC_DIR="/Users/you/my-idea/spec"

      Validate at any time:
        forge validate
```

Open an agent session in that directory and describe your idea. The relevant skill activates; the interview begins.

---

## CLI

| Command | Purpose |
|---|---|
| `forge init` | Scaffold a new project (`spec/` + `framework.yaml` + `conception.yaml`) |
| `forge update` | Refresh `framework.yaml` to the current Forge version |
| `forge --version` | Print the installed Forge CLI version |
| `forge list [--kind K]` | Enumerate nodes in the spec dir |
| `forge inspect <id>` | Lightweight metadata probe |
| `forge context <element-id>` | Full implementation-ready bundle for an element |
| `forge find <query>` | Substring search across IDs and descriptions |
| `forge validate` | Lint the spec for structural and referential errors |
| `forge graph` | Visualise the dependency graph |

Spec-dir resolution order: `--spec-dir` flag > `$FORGE_SPEC_DIR` env var > auto-discover (walks upward looking for `spec/conception.yaml`).

---

## The six skills

| Skill | Role | Input | Output |
|---|---|---|---|
| **forge-design** | System designer / interviewer | Vague product idea | conception.yaml, system.yaml, domain.yaml files, module.yaml skeletons, workbench/discovery.md |
| **forge-spec** | Element elicitation | One module | Elements, properties, operations, types, errors, contracts, interactions, flows, datastores |
| **forge-cast** | Codebase hydration | Existing non-Forge codebase | Draft Forge spec corpus anchored to repository evidence, workbench/cast-report.md |
| **forge-review** | Quality + security review | Completed module specs | Completeness, consistency, contract correctness, attack vector analysis, workbench/review.md |
| **forge-build** | Implementation orchestrator | Reviewed spec corpus | Code + tests dispatched via parallel subagents, each using `forge context <id>` |
| **forge-validate** | Post-implementation validator | Implemented system + spec | Static analysis, test coverage, behavioral probes, workbench/validation.md |

Skills activate via natural-language prompts in any supported client, or slash-commands where the client supports them.

---

## The spec system

Hierarchical YAML — one file per node, IDs derived from file paths.

| Level | Node type | File location |
|---|---|---|
| Conception | conception | `spec/conception.yaml` |
| System | system | `spec/<system>/system.yaml` |
| Domain | domain | `spec/<system>/<domain>/domain.yaml` |
| Module | module | `spec/<system>/<domain>/<module>/module.yaml` |
| Element | element | `spec/<system>/<domain>/<module>/<element>.yaml` |
| Registry | type, error, policy, contract, integration, interaction, flow | `spec/<system>/<registry>/` |
| Implementation | datastore, environment, test, deployment | `spec/<system>/implementation/` |

Process artifacts (discovery notes, review reports, build plans) live in `spec/<system>/workbench/`.

Full schema reference: [`docs/framework-reference.md`](docs/framework-reference.md).

---

## Repository layout

```
forge/
├── src/
│   └── cli/              Python CLI package (the forge command)
├── .agents/skills/       The 6 forge skills
│   ├── forge-design/
│   ├── forge-spec/
│   ├── forge-cast/
│   ├── forge-review/
│   ├── forge-build/
│   └── forge-validate/
├── docs/
│   └── framework-reference.md  Combined schema + enum + rule reference
├── example/
│   └── spec/             Working example spec (LinkHub URL shortener)
├── scripts/
│   └── install-skills.sh Global skill install + CLI symlink
├── tests/                pytest suite — 74 tests
├── pyproject.toml
└── README.md
```

---

## Development

### Testing

```bash
.venv/bin/pytest -v
```

The `example/spec/` directory is a complete working spec (LinkHub, a URL shortener) that doubles as the test fixture and a reference for what a finished project looks like.

```bash
export FORGE_SPEC_DIR="$(pwd)/example/spec"
forge list                                                    # see all nodes
forge context linkhub.shortener.links.link_manager.short_link # full element bundle
forge find redirect                                            # search across nodes
forge validate                                                 # lint the spec
```

### Adding a new skill

1. Create `.agents/skills/<name>/SKILL.md` with agentskills.io frontmatter (`name`, `description`).
2. Symlink `references/framework.md` → `../../../../docs/framework-reference.md` for framework access.
3. Add the skill to `SKILLS=()` in `scripts/install-skills.sh`.
4. `./scripts/install-skills.sh install` to wire up globally.

### Uninstall

```bash
./scripts/install-skills.sh uninstall
```

Removes all global skill symlinks and the `forge` CLI binary. Does not touch project `spec/` directories.

---

## Contributing

Pull requests welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for:

- Branching and commit conventions (Conventional Commits)
- Local dev setup
- PR requirements and CI expectations
- Release process

Changes are tracked in [`CHANGELOG.md`](CHANGELOG.md) following [Keep a Changelog](https://keepachangelog.com).

## Security

Security issues: see [`SECURITY.md`](SECURITY.md). Do not open public issues for vulnerabilities.

## License

MIT — see [`LICENSE`](LICENSE).

---

<div align="center">

<sub>Built for agent-driven development. Questions over prompts. Specs over intentions. Code follows.</sub>

</div>
