---
name: forge-plan
description: >
  Forge V2 planning skill. Use when the schema is coherent enough to derive an implementation plan.
  Starts draft-first from the current schema, then asks only the unresolved build-order, repo-layout,
  or operator-check questions that affect execution. Produces a machine-readable, human-readable build
  plan in forge/workbench.
---

# forge-plan

Read before starting:

- `docs/forge-v2-schema.md`
- `docs/forge-v2-architecture.md`
- `frameworks/plan/FRAMEWORK.md`
- current files under `forge/`

## Purpose

Turn schema truth into the next smallest safe implementation slices.

This stage owns:

- `forge/workbench/plan.yaml`
- optionally `forge/workbench/plan.md`

## Core Behavior

This is a draft-first stage.

Do not begin with a broad interview. Instead:

1. derive a first-pass plan from bootstrap, flows, units, and operations
2. present the draft
3. ask only the unresolved questions that change slice ordering, repo layout, or verification shape
4. finalize the plan

## Non-negotiables

1. Bootstrap comes first.
2. Every slice must preserve or expand runnable capability.
3. Every slice must list required checks.
4. Operator checks must be explicit when automation is weak.
5. The canonical artifact is YAML, readable by both humans and agents.

## Draft Inputs

Use:

- `forge/bootstrap.yaml`
- `forge/build_policy.yaml`
- `forge/flows/*.yaml`
- `forge/operations/*.yaml`
- `forge/units/*.yaml`
- `forge/verification/**/*`
- `forge/workbench/discovery.md`

## Planning Process

### Step 1 — System Assessment

Before asking anything:

- identify the bootstrap path
- identify the units required to make it runnable
- identify the operations and surfaces on that path
- identify the checks that must prove it still works

### Step 2 — Draft the Plan

Write a first-pass plan mentally before asking the human questions.

At minimum, the draft must identify:

- bootstrap slice
- bootstrap hardening slice
- next adjacent vertical slice
- checks after each slice
- operator checks if any

### Step 3 — Ask Only Unresolved Questions

Valid questions here are things like:

- Does the repo layout need to follow a different source-root pattern than the inferred default?
- Should two slices land separately or together because of operational coupling?
- Does bootstrap require a human operator checkpoint before expansion?
- Is there any implementation layout constraint that would change file targeting?

Do not ask open-ended product or domain questions at this stage.

### Step 4 — Write the Canonical Plan

Write `forge/workbench/plan.yaml` with:

- target
- summary
- slices
- touched schema IDs
- checks
- operator checks
- status

Optionally render `forge/workbench/plan.md` for a prose version.

## Completion

Before exiting:

1. summarize the slices
2. explicitly identify the first execution slice
3. ask for confirmation if any architecture-affecting ambiguity remains

## Key Constraints

- Plan references schema IDs, not code paths, as primary truth.
- Plan is a workbench artifact, not schema truth.
- If bootstrap is not yet concrete enough to plan, route back to `forge-discover` or `forge-spec`.
