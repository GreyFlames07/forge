---
name: forge-build
description: >
  Forge V2 build skill. Use when the schema is complete enough for the target slices, the plan exists,
  and the user wants working implementation code and tests generated while preserving runnability. Acts
  as an orchestrator: validates readiness, consults the plan, dispatches implementation work using
  forge context, checks bootstrap continuously, and updates workbench status and validation evidence.
---

# forge-build

Read before starting:

- `docs/forge-v2-schema.md`
- `docs/forge-v2-architecture.md`
- `frameworks/build/FRAMEWORK.md`
- `forge/workbench/discovery.md`
- `forge/workbench/plan.yaml`

## Purpose

Implement the planned slices while keeping the system runnable.

This stage is not a free-form code generator. It is a bootstrap-first implementation orchestrator.

## Non-negotiables

1. Bootstrap first. No broad implementation before the bootstrap path exists.
2. Run bootstrap as early as possible.
3. Build against the running bootstrap when possible.
4. Re-check startup, bootstrap, and affected flows after each material slice.
5. If automation is insufficient, require operator verification instead of pretending coverage exists.
6. Schema files are frozen during a build run. Do not silently edit schema truth to make implementation easier.

## Inputs

- schema under `forge/`
- `forge/workbench/plan.yaml`
- existing repo state
- verification items

## Workbench Outputs

- `forge/workbench/status.yaml`
- `forge/workbench/validation.md`

## Step 1 — Readiness Gate

Before writing code:

1. inspect the plan
2. inspect the bootstrap definition
3. run `forge validate --schema-only` if available
4. stop if the schema is structurally invalid

If bootstrap is underspecified, route back to `forge-spec` or `forge-plan` rather than guessing.

## Step 2 — Bootstrap Assessment

Establish:

- whether bootstrap already exists in runnable form
- what commands or checks prove it
- what operator verification is required

If bootstrap does not exist yet:

- implement the minimum bootstrap slice first
- do not parallelize expansion work ahead of it

## Step 3 — Execution Plan

Work slice by slice from `forge/workbench/plan.yaml`.

For each slice:

1. load schema context through `forge context`
2. identify touched units, operations, surfaces, flows, and stores
3. implement the smallest complete version of that slice
4. run the declared checks
5. update workbench status

## Step 4 — Subagent Dispatch

When delegation is useful, subagents should receive:

- the slice or target ID
- the instruction to call `forge context <id>`
- the architecture and layout rules implied by the repo and plan
- the requirement to implement exactly what the schema declares

Subagents should not be given giant inlined schema dumps when the CLI can provide context directly.

## Step 5 — Failure Handling

If a slice fails:

1. identify whether the failure is implementation, architecture, or schema ambiguity
2. retry implementation failures with specific feedback
3. stop immediately on schema ambiguity and surface it to the human
4. if bootstrap breaks, repair bootstrap before continuing

## Completion

When a slice lands:

1. record status in `forge/workbench/status.yaml`
2. record validation evidence in `forge/workbench/validation.md`
3. state whether bootstrap was preserved, expanded, or regressed

When all planned slices for the run are complete:

1. summarize files written
2. summarize bootstrap health
3. recommend `forge-validate`

## Key Constraints

- Do not continue building through a broken bootstrap.
- Do not claim a slice is done without running its declared checks.
- Do not hide operator-required checks in prose; they must correspond to verification items.
