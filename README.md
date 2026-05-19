# Forge

Forge is a Python CLI and framework for vertical-first system design and
delivery. It helps you define a system clearly, split it into buildable
verticals, and then deepen and implement one slice at a time with the minimum
context needed for the task at hand.

Forge is **skills-first**. The skills drive the work. The CLI exists to provide
scoped context, validation, and audit artifacts to the active skill.

## What This Repository Contains

- `src/cli`: the Forge CLI implementation
- `skills/`: the Forge skill source used by initialized repositories
- `FRAMEWORK_V3.md`: the framework process and recommended authoring order
- `SCHEMA_REFERENCE_V3.md`: the schema contract and field rules
- `examples/`: example Forge repositories and audit artifacts

## CLI Commands

- `forge init`: scaffold a new Forge workspace and explain how to use it
- `forge context`: render scoped context for a system, vertical, flow,
  container, or component
- `forge audit`: generate a self-contained architecture audit dashboard

## What Forge Is

- a framework for capturing architectural truth before implementation detail
- a skills-first workflow for moving from broad system design to one thin
  vertical at a time
- a scoped context generator for build, review, and security tasks
- an audit artifact generator for human review

## What Forge Is Not

- a generic project scaffolder for arbitrary app stacks
- a replacement for implementation skills such as build, review, and security
- a reason to model every payload, component, or environment detail up front
- an excuse to widen a vertical beyond what can be built and validated cleanly

## Recommended Workflow

1. Run `forge init` in an empty repository.
2. Read:
   - `docs/USING_FORGE.md`
   - `docs/FRAMEWORK_V3.md`
   - `docs/SCHEMA_REFERENCE_V3.md`
3. Use `forge-schema` to define:
   - `system.yaml`
   - `high_level_flows/`
   - `early_state.yaml`
   - `runtime.yaml`
4. Derive `verticals/` once the runtime picture is clear.
5. Pick one vertical and deepen it through:
   - `runtime_flows/`
   - `data_shapes/`
   - `persistent_shapes/`
   - `containers/`
   - `deployment.yaml`
6. Use `forge-review` to check the slice for drift, bloat, and broken references before build starts.
7. Use `forge-security` to make the slice security posture explicit before build starts.
8. Use `forge-build` to plan or implement that approved vertical.

The intended operating mode is:

1. choose the active skill first
2. ask that skill what scope it needs
3. use `forge context` only for that narrow scope
4. use `forge audit` when you need a whole-system review artifact

## Golden Path Examples

- `examples/forge_v2_ordering_example`: the compact canonical example for docs,
  smoke tests, and first-time users
- `examples/forge_v2_fulfillment_control_example`: the richer example used to
  pressure-test flows, data, deployment, and audit rendering

## Local Development

Use the project virtual environment:

```bash
.venv/bin/python -m pip install -e .[dev]
```

## Validation Commands

```bash
make lint
make typecheck
make test
make compile
make build
make verify-package
make smoke-init
make check
```

`make verify-package` builds the wheel, installs it into a fresh Python 3.11+
virtual environment, and confirms that the installed `forge` entrypoint works.

## Packaging

Build artifacts are generated with:

```bash
.venv/bin/python -m build
```

This produces:

- `dist/*.tar.gz`
- `dist/*.whl`

Validate package metadata before release with:

```bash
make check-dist
```

## Local Testing

Run the full local verification path:

```bash
make check
```

That covers linting, type checking, tests, compile validation, build output,
distribution metadata checks, clean wheel install, and `forge init` smoke
validation.

If you want to test the richer example schema directly:

```bash
EXAMPLE="examples/forge_v2_fulfillment_control_example"
.venv/bin/forge audit --project-dir "$EXAMPLE" --output /tmp/forge-audit-example.html
```

That generates the audit artifact and opens it unless `--no-open` is supplied.

## Framework Notes

- Forge is vertical-first: model broadly, then deepen one thin slice.
- The framework should reduce context, not increase it.
- Components and exact schemas should only appear when runtime boundaries and
  vertical intent are already clear.
- Important decisions should be captured in `decision_notes.md`.

## Maintainer Notes

- Release instructions live in [docs/RELEASING.md](/Users/willdefina/Documents/2026%20-%20Business/dev-tools/forge/docs/RELEASING.md).

## Repository Notes

Previous iteration artifacts have been retained in `old-forge-v2/`.
