# Forge

Forge is a Python CLI and framework for V4 system design and delivery. It keeps
C1/C2 architecture central, keeps C3 implementation architecture beside code,
and gives skills narrow context from the merged model.

Forge is **skills-first**. The skills drive the work. The CLI exists to provide
scoped context, validation, and audit artifacts to the active skill.

## What This Repository Contains

- `src/cli`: the Forge CLI implementation
- `skills/`: the Forge skill source used by initialized repositories
- `FRAMEWORK_V4.md`: the V4 framework process used to seed `forge/FRAMEWORK_V4.md`
- `SCHEMA_REFERENCE_V4.md`: the V4 schema contract used to seed `forge/SCHEMA_REFERENCE_V4.md`
- `examples/`: example Forge repositories and audit artifacts

## CLI Commands

- `forge init`: scaffold a new Forge workspace and explain how to use it
- `forge crawl`: extract the merged V4 model from central files and code annotations
- `forge context`: render scoped context for a system, flow, container, entity,
  component, operation, or data shape
- `forge audit`: generate a self-contained architecture audit dashboard

## What Forge Is

- a framework for capturing architectural truth before implementation detail
- a skills-first workflow for moving from business discovery to one thin build slice
- a scoped context generator for build, review, and security tasks
- an audit artifact generator for human review

## What Forge Is Not

- a generic project scaffolder for arbitrary app stacks
- a replacement for implementation skills such as build, review, and security
- a reason to model every payload, component, or environment detail up front
- an excuse to widen a build slice beyond what can be built and validated cleanly

## Recommended Workflow

1. Run `forge init` in an empty repository.
2. Read:
   - `forge/USING_FORGE.md`
   - `forge/FRAMEWORK_V4.md`
   - `forge/SCHEMA_REFERENCE_V4.md`
3. Use `forge-business` to create `business-plan.md` for new ideas.
4. Use `forge-schema` to define:
   - `forge/system.yaml`
   - `forge/containers.yaml`
   - `forge/entities.yaml`
   - `forge/decisions.yaml`
   - `forge/crawler.yaml`
5. Use `forge-hydrate` when an existing codebase needs to be reverse-engineered into Forge V4.
6. Use business actions to speculate cross-container runtime flows before settling containers.
7. Add C3 annotations beside implementation code as the slice is built.
8. Use `forge crawl`, `forge context`, and `forge audit` to validate the merged model.
9. Use `forge-review` and `forge-security` before build work.
10. Use `forge-build` to plan or implement the approved slice.

The intended operating mode is:

1. choose the active skill first
2. ask that skill what scope it needs
3. use `forge crawl` to validate extraction
4. use `forge context` only for narrow scope
5. use `forge audit` when you need a review artifact

An initialized repository keeps the Forge-owned schema workspace under `./forge/`. The repo root stays available for product code, app docs, and non-Forge tooling.

## Golden Path Examples

- `examples/forge_minimal_web_app`: the V4 example used for docs, smoke tests,
  crawler extraction, context, and audit rendering

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
EXAMPLE="examples/forge_minimal_web_app"
.venv/bin/forge audit --project-dir "$EXAMPLE" --output /tmp/forge-audit-example.html
```

That generates the audit artifact and opens it unless `--no-open` is supplied.

## Framework Notes

- Forge is slice-first: model broadly, then deepen one thin build slice.
- The framework should reduce context, not increase it.
- Components and exact schemas should only appear when runtime boundaries and
  business action intent are already clear.
- Important decisions should be captured in `forge/decisions.yaml`.

## Maintainer Notes

- Release instructions live in [docs/RELEASING.md](/Users/willdefina/Documents/2026%20-%20Business/dev-tools/forge/docs/RELEASING.md).
