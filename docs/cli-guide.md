# Forge CLI — Full Guide

`forge` is a context walker for the Forge L0–L5 spec system. Its one job: given an id, assemble every piece of specification context an agent needs to implement that entity — the target spec, the L0 entries it references, its owning module, applicable policies, L1 conventions, L4 callers, and L5 operations — into a single bundle.

You do not use `forge` to write specs. You use it to read them in a form shaped for implementation.

---

## Why this tool exists

An atom's behavior is defined across six files: its own spec (L3), the types and errors it references (L0), its owning module's policies and permissions (L2), project-wide conventions (L1), the flows that call it (L4), and runtime operations (L5). Opening all of those manually, slicing out the relevant parts, and feeding them to an agent is tedious and error-prone. `forge context <id>` does it in one invocation and emits a single document.

The walker slices L0 — pulling only the types, errors, constants, markers, and external schemas actually referenced — rather than dumping the whole registry. For a typical atom this saves 50–60% of tokens versus reading the raw YAML files whole.

---

## Install

Requires Python 3.11 or newer.

```bash
# From the repo root:
uv venv --python 3.13 .venv
uv pip install -e .

# Verify:
.venv/bin/forge --help
```

For convenience, activate the venv or add `.venv/bin` to your `PATH`.

---

## Spec directory resolution

Every command needs to know where specs live. Resolution order:

1. `--spec-dir <path>` — explicit flag
2. `$FORGE_SPEC_DIR` — environment variable
3. Auto-discover — walk upward from the current working directory, looking for either `L0_registry.yaml`, `.forge/L0_registry.yaml`, `.forge/` (with L-layer structure — picks up projects just after `forge init` before discover runs), or `forge/docs/L0_registry.yaml` (legacy).

The auto-discover default matches the canonical layout produced by `forge init`: the spec dir is `.forge/` at the project root, and `forge` finds it from anywhere inside the project tree.

For testing, point at `src/example/`:

```bash
export FORGE_SPEC_DIR="$(pwd)/src/example"
# or pass --spec-dir src/example to each command
```

---

## Commands

### `forge --version`

Print the installed Forge CLI version.

```bash
forge --version
```

Example output:

```text
forge 0.1.0
```

---

### `forge update`

Refresh the init-managed project assets in the current project.

```bash
forge update
forge update --spec-subdir specs
forge update --skip-skills
```

`forge update` refreshes the same project-managed assets that `forge init` lays down:

- the spec directory structure (`.forge/` or your custom `--spec-subdir`)
- schema template symlinks under `<spec-dir>/templates/`
- project-local skill symlinks under `.claude/skills/`, `.codex/skills/`, and `.agents/skills/`

It does **not** overwrite authored spec YAML files such as `L0_registry.yaml`, `L1_conventions.yaml`, module specs, atom specs, flows, or journeys. After refresh it prints the recommended `/forge-audit` follow-up.

**Options**

| Flag | Default | Description |
|---|---|---|
| `--spec-subdir PATH` | `.forge` | Relative path from the project root for the spec directory. |
| `--skip-skills` | off | Refresh only the spec directory and schema templates; skip skill symlink refresh. |

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Managed assets refreshed successfully. |
| `1` | No Forge project detected at the requested spec directory, or Forge sources could not be located. |

---

### `forge context <id>`

Build the full implementation-ready bundle.

```bash
forge context atm.pay.charge_card
forge context PAY --format markdown
forge context flow.process_order_payment --format json
```

Accepted ids: atoms (`atm.*`), modules (`^[A-Z]{3}$`), journeys (`jrn.*`), flows (`flow.*`), artifacts (`art.*`). Other ids (types, errors, constants, policies, markers, external schemas) are not bundleable — they are leaf references, not implementation targets. Use `inspect` for those.

**Options**

| Flag | Default | Description |
|---|---|---|
| `--spec-dir PATH` | auto | Path to the spec directory. |
| `--format {yaml,json,markdown}` | `yaml` | Output format. |

**Output formats**

- `yaml` (default) — most token-efficient, diffable, round-trippable. Use this for agent consumption.
- `json` — strict parseable. Use when piping into a programmatic consumer.
- `markdown` — wraps each section in a heading plus fenced YAML block. Use when pasting into a chat or a design doc.

**Exit codes**

| Code | Meaning |
|---|---|
| `0` | Bundle emitted, all references resolved. |
| `1` | Usage error (unknown id, non-bundleable kind, missing spec dir). |
| `2` | Bundle emitted, but one or more referenced ids could not be resolved. Unresolved list printed to stderr. |

`2` is a warning, not a failure — the bundle is still usable. It indicates the spec set is incomplete (referenced atoms have no spec file yet). In CI, treat `2` as "work in progress."

---

### `forge list [--kind KIND]`

Enumerate ids in the spec directory.

```bash
forge list                              # all ids grouped by kind
forge list --kind atom                  # only atoms
forge list --kind error                 # only L0 error codes
forge list --kind atom --ids-only       # bare ids, one per line (pipe-ready)
```

**Options**

| Flag | Default | Description |
|---|---|---|
| `--kind KIND` | all | Restrict to one kind. Values: `atom`, `module`, `journey`, `flow`, `artifact`, `policy`, `type`, `error`, `constant`, `external_schema`, `marker`. |
| `--ids-only` | off | Emit ids only, without headers or descriptions. Intended for piping. |
| `--spec-dir PATH` | auto | Path to the spec directory. |

**Pipe patterns**

```bash
# Build bundles for every atom in a shell loop:
forge list --kind atom --ids-only | while read id; do
  forge context "$id" > "bundles/${id}.yaml"
done

# Count entities by kind:
forge list --ids-only | wc -l
```

---

### `forge inspect <id>`

Lightweight metadata probe — answers "does this exist and what is it?" without the cost of a full bundle walk.

```bash
forge inspect atm.pay.charge_card
forge inspect PAY
forge inspect PAY.VAL.001       # works for L0 entries too
```

Output fields vary by kind:

| Kind | Extra fields shown |
|---|---|
| `atom` | `atom_kind`, `owner_module`, `side_effects`, `output_errors` |
| `module` | `owned_atoms`, `owned_artifacts`, `dependency_whitelist`, `policies` |
| `flow` | `transaction_boundary`, `trigger`, `steps` |
| `journey` | `surface`, `states`, `exit_states` |
| `artifact` | `owner_module`, `format`, `produced_by`, `consumers` |
| `error` | `category`, `message` |
| `type` | `type_kind`, `fields` (entity) or `values` (enum) |
| `constant` | `type`, `value` |
| `external_schema` | `provider`, `base_url`, `auth_method` |

Every inspection also reports `bundleable: true|false` and, when true, the exact `bundle_command` to run. Use `inspect` before `context` when you're not sure an id is valid.

---

### `forge find <query>`

Case-insensitive substring search across every entity's ID and description. Designed for the **reuse-before-create** checks the skills run before creating a new entity — fast scanning to surface potential matches at the moment of creation, when consolidation is cheapest.

```bash
forge find charge                                # all entities mentioning "charge"
forge find charge --kind atom                    # atoms only
forge find declined --kind error                 # errors whose message mentions "declined"
forge find charge --limit 5                      # top 5 by relevance
forge find charge --limit 0                      # no limit
```

**Options**

| Flag | Default | Description |
|---|---|---|
| `--kind KIND` | all | Restrict to one kind (same values as `forge list --kind`). |
| `--limit N` | 10 | Maximum matches to show. `0` means unlimited. |
| `--spec-dir PATH` | auto | Path to the spec directory. |

**Output format**

Each match shows: id, kind, match signal (`[id]`, `[desc]`, or `[id+desc]`), one-line description.

```
# forge find 'charge' — 10 matches

  atm.pay.charge_card         atom      [id+desc]   Charges a registered payment method for a given amount...
  atm.pay.charges_schema      atom      [id+desc]   Declares the desired state of the charges table...
  MAX_CHARGE_CENTS            constant  [id+desc]   Maximum single-charge amount ($100,000)...
  PAY                         module    [desc]      Handles all payment operations including charging...
  ...
```

Ranking: matches on both id and description rank above single-match hits. Ties break by kind priority (atoms/modules first) then alphabetical.

**How the skills use it**

- `forge-discover` sub-phase 2: before committing a new module file, scan for existing modules with overlapping concerns — surface any matches advisorily before the write.
- `forge-decompose` sub-phase 1 (Pass 2.5): sweep candidate atoms against the whole project to catch cross-module duplicates before classification commits to names.
- `forge-decompose` sub-phase 2 Part B: per-atom scan before committing each stub file.

---

## What's in a bundle

The walker produces different sections depending on the target kind. Sections with no content are omitted.

### atom bundle

| Section | Contents |
|---|---|
| `l0_registry_slice` | Only the types, errors (plus `SYS.SYS.999` from L1 propagation), constants (`const.X` references), markers (from `side_effects`), and external schemas (`external.X.*` references) this atom touches. Referenced error categories are pulled in alongside the errors. Transitive type references are resolved. |
| `l1_conventions` | The full L1 file. It's small (<200 lines) and universally relevant. |
| `l2_module` | The owning module's full spec. |
| `policies_applied` | Only the policies whose `applies_when` predicate matches this atom (not every policy listed on the module). |
| `l3_atom` | The atom spec itself. |
| `called_atom_signatures` | For every atom this one calls: kind, description, input, output, side_effects — **signatures only**, not full specs. |
| `training_artifact` | (MODEL atoms only.) Full spec of `training_contract.data_source`. |
| `l4_callers` | Orchestrations and journeys that invoke this atom, with the specific step/transition context, and a derived `implications` list explaining what the caller requires (retry safety, compensability, saga semantics). |
| `l5_operations` | The full L5 file. |

**Why the L4 implications matter.** An atom's spec doesn't say "must be retry-safe." The flow that calls it with `on_error: RETRY(max=3)` does. The walker extracts that context and states the requirement explicitly so the implementing agent cannot miss it.

### module bundle

Full spec + every owned atom (fully expanded, not signatures), every owned artifact, applied policies, whitelisted module interfaces (signatures of modules listed in `dependency_whitelist`), aggregate L0 slice, L1, and L5.

### journey bundle

Full spec + every L2 entry point that invokes this journey + every handler atom (full) + every invoked orchestration (full) + aggregate L0 slice + L1 + L5.

### flow bundle

Full spec + trigger payload type + signatures of every atom invoked in `sequence` and every compensation atom + L2 entry points that invoke this flow + aggregate L0 slice + L1 + L5.

### artifact bundle

Full spec + owner module + schema type (if the artifact's `schema` points at an L0 entity) + producer atom signature (from `provenance.produced_by`) + source artifacts (shallow) + consumer atom signatures.

---

## Unresolved references

When the walker hits an id that isn't in the index — typically a called atom whose spec file hasn't been written yet — it emits `status: UNRESOLVED` in place of the signature and lists the id on stderr:

```
# Unresolved references (3):
#   - atm.usr.fetch_customer
#   - atm.pay.find_by_idempotency_key
#   - atm.pay.persist_charge
```

Exit code 2 signals this state. The bundle is still emitted — the implementing agent can read it, note which contracts are missing, and either define them or flag the gap. Unresolved refs are a feature during spec-driven development: they tell you what's left to specify.

---

## Integration patterns

### Feeding a bundle to Claude Code

```bash
forge context atm.pay.charge_card --format markdown > /tmp/ctx.md
claude "Implement the atom specified in /tmp/ctx.md in TypeScript."
```

Or inline:

```bash
claude "$(forge context atm.pay.charge_card --format markdown)"
```

### Rebuilding bundles on every CI run

```bash
forge list --kind atom --ids-only | while read id; do
  forge context "$id" --format yaml > "build/ctx/${id}.yaml" || exit $?
done
```

Fail CI on exit code 1 (usage / parse error) but tolerate 2 (unresolved refs) — those are the work items.

### Checking a spec set before committing

```bash
# Every atom resolves everything it references:
forge list --kind atom --ids-only | while read id; do
  forge context "$id" > /dev/null 2>&1 && echo "OK $id" || echo "FAIL $id"
done
```

---

## Troubleshooting

**"Cannot locate spec dir."**
Auto-discovery didn't find `L0_registry.yaml`. Pass `--spec-dir` explicitly, set `$FORGE_SPEC_DIR`, or `cd` somewhere inside the repo tree.

**"mapping values are not allowed here" (YAML parse error on load)**
A spec file contains an unquoted flow-style string — typically a logic or render_contract list entry with `{ ... }` and colons inside. Wrap the offending list item in single quotes. This is a spec-file bug, not a CLI bug.

**"X is a type/error/constant; only [atom, module, journey, flow, artifact] can be bundled via `forge context`."**
Use `forge inspect <id>` instead. L0 entries are leaf references surfaced inside bundles; they are not implementation targets.

**Unresolved atom references when you expect them to resolve**
Run `forge list --kind atom --ids-only | grep <partial>` to check spelling, or `forge inspect <id>` to verify the entity exists at all. Naming_ledger regex mismatches are also possible — the id must match the L0 regex for its kind.

---

## What the CLI deliberately does not do

- **No validation.** `forge context` assembles context. It does not check that your spec conforms to the L0–L5 schemas. Schema validation is a separate concern.
- **No spec generation.** It reads what's there; it doesn't scaffold new atoms.
- **No graph queries beyond walking.** There's no `forge who-calls <id>` or `forge depends-on <id>` — those can be grepped or added later if needed. The design principle is: one walk, one output, shaped for implementation.
- **No caching.** Each invocation re-reads and re-indexes the spec directory. Spec files are tiny; the overhead is imperceptible. Skipping the cache keeps the mental model simple.

---

## Architecture

```
src/cli/
├── __init__.py
├── __main__.py          # entry for `python -m cli`
├── forge.py             # thin entry: iterate ALL_COMMANDS, register, dispatch
├── common.py            # shared helpers: spec-dir load, id suggest, describe
├── index.py             # load spec dir, build flat id->Entry map, explode L0
├── walker.py            # 5 per-kind expanders + L4 caller scanner + policy predicate eval
├── bundle.py            # YAML / JSON / markdown formatters, section headers
└── commands/
    ├── __init__.py      # ALL_COMMANDS list — one entry per command
    ├── base.py          # module contract (docstring)
    ├── context.py       # forge context
    ├── list_cmd.py      # forge list
    └── inspect.py       # forge inspect
```

Two phases per invocation:
1. **Index** — walk the spec dir, load every YAML, explode L0 into individual entries, build a single dict keyed by id.
2. **Walk** — dispatch by kind from `naming_ledger` regex match, BFS from the target id, dedup via visited set, assemble an ordered dict of sections, hand to the formatter.

The walker, formatter, and command modules are decoupled. Adding a new format (e.g. `jsonl` for streaming, or `toml`) is one function in `bundle.py`. Adding a new command is one file in `commands/` plus one line in `commands/__init__.py`.

---

## Extending the CLI

Every command is an independent module. To add one:

### 1. Copy the contract

Each command module must expose four names:

| Name | Type | Purpose |
|---|---|---|
| `NAME` | `str` | Subcommand name — what the user types after `forge`. |
| `HELP` | `str` | Short help line shown in `forge --help`. |
| `register(sub)` | function | Build your subparser; call `sub.add_parser(NAME, ...)` and `set_defaults(handler=run)`. |
| `run(args)` | function | Execute the command; return `0` (success), `1` (usage error), or `2` (soft warning). |

### 2. Write the module

Drop a file at `src/cli/commands/<name>.py`. Minimal skeleton:

```python
"""`forge validate` — check a spec file against its schema (example)."""

from __future__ import annotations

import argparse

from cli import common

NAME = "validate"
HELP = "Validate a spec file against its L-layer schema."
DESCRIPTION = "..."


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument("path", help="Path to the spec file to validate.")
    common.add_spec_dir_arg(p)
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    idx, rc = common.load_index(args.spec_dir)
    if rc != 0:
        return rc
    # ... your logic ...
    return 0
```

Reuse helpers from `cli.common` instead of reimplementing them:

| Helper | Purpose |
|---|---|
| `add_spec_dir_arg(parser)` | Adds the standard `--spec-dir` flag. |
| `load_index(spec_dir_arg)` | Resolves spec dir, loads index. Returns `(idx, 0)` on success or `(None, 1)` with error already on stderr. |
| `suggest_similar(idx, target)` | Prints "Did you mean:" for typo'd ids. |
| `full_description(data)` / `one_line_description(data)` | Pull the `description` field uniformly across kinds. |
| `BUNDLEABLE_KINDS`, `ALL_KINDS` | Shared kind constants. |

### 3. Register it

Open `src/cli/commands/__init__.py` and add the import plus the entry:

```python
from cli.commands import validate as _validate

ALL_COMMANDS = [
    _context,
    _list_cmd,
    _inspect,
    _validate,      # <-- new
]
```

That's the full extension path. `forge.py` auto-registers every module in `ALL_COMMANDS` and dispatches via `args.handler` — you never edit the entry point.

### 4. Test it

Add a `tests/test_<command>.py` that calls `cli.forge.main(["<name>", ...])` and asserts on captured stdout/stderr/exit-code. The pattern is in `tests/test_cli.py`.

### Design principles for new commands

- **One responsibility per command.** If you're tempted to add `--dry-run` or `--batch` modes that fundamentally change behavior, that's two commands.
- **Exit codes matter.** `0` = clean success, `1` = user error (stderr has the reason), `2` = soft warning (output still usable). Agents and CI scripts rely on these.
- **stdout is output, stderr is narration.** Anything a pipe consumer would want goes to stdout; everything else (progress, warnings, suggestions) goes to stderr.
- **Don't reach into another command's internals.** If two commands need the same helper, it belongs in `common.py`.
