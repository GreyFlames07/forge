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

`forge/workbench/*` files are internal framework artifacts in V2. They are produced and consumed by the stage skills; they are not separate public CLI commands.

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

## Source Control Outputs

At each meaningful checkpoint, the build stage should also update source control state.

Checkpoint examples:

- bootstrap first becomes runnable
- a planned slice lands
- a meaningful runtime or contract change lands without breaking bootstrap

Expected behavior:

1. inspect git state
2. summarize the checkpoint in plain language
3. create a checkpoint commit when the human or repo policy allows it
4. push or update the GitHub branch when a remote exists and credentials are available
5. if push is not possible, stop at a clean local checkpoint and record the next action explicitly

## Step 1 — Readiness Gate

Before writing code:

1. inspect the plan
2. inspect the bootstrap definition
3. use `forge list` and `forge context` to confirm the relevant schema objects and IDs
4. stop if the schema is structurally ambiguous or incomplete

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
6. update git/GitHub at the slice checkpoint when the change is meaningful

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

## Step 6 — Checkpoint Source Control

At each checkpoint:

1. confirm bootstrap and the touched slice still work at the declared level
2. review `git status`
3. prepare a checkpoint summary tied to the slice or bootstrap milestone
4. create a checkpoint commit if permitted
5. push the branch or update the open GitHub branch if permitted and possible

Do not batch many meaningful slice landings into one opaque commit when the framework can keep checkpoints intelligible.

## Failure Routing

- If bootstrap is missing or underspecified, stop and route back to `forge-plan` or `forge-spec`.
- If implementation pressure reveals missing or conflicting contracts, stop and route back to `forge-spec` instead of mutating schema truth ad hoc.
- If the current plan no longer reflects the real execution order, stop and route back to `forge-plan`.
- If operator verification is required before expansion, stop after bootstrap hardening and hand off to `forge-validate` or the human operator.
- If a GitHub update is required by the workflow but remote state, permissions, or branch policy block it, stop and surface that operational blocker instead of silently continuing.

## Completion

When a slice lands:

1. record status in `forge/workbench/status.yaml`
2. record validation evidence in `forge/workbench/validation.md`
3. state whether bootstrap was preserved, expanded, or regressed
4. state whether the checkpoint was committed locally, pushed to GitHub, or blocked operationally

When all planned slices for the run are complete:

1. summarize files written
2. summarize bootstrap health
3. recommend `forge-validate`

## Key Constraints

- Do not continue building through a broken bootstrap.
- Do not claim a slice is done without running its declared checks.
- Do not hide operator-required checks in prose; they must correspond to verification items.
