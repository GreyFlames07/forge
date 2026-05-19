---
name: forge-build
description: Plan and build a Forge V2 vertical slice. Use when the user wants to implement a chosen vertical from the Forge V2 schema after it has already passed `forge-review` and `forge-security`, or when the user is explicitly resolving findings from those pre-build passes. If no build plan exists for that vertical, create the build plan first; otherwise execute the build. Use when implementation must proceed in thin vertical slices, follow a TDD-style workflow, and be validated through unit, integration, and full-system testing in the real build environment.
---

# forge-build

Read before starting:

- `../../SCHEMA_REFERENCE_V3.md`
- `../forge-schema/SKILL.md`
- `../forge-review/SKILL.md`
- `../forge-security/SKILL.md`

Prefer when available:

- Forge CLI `init`
- Forge CLI `context`
- Forge CLI `audit`

Maintain throughout the workflow:

- `../../decision_notes.md`

## Purpose

Handle both planning and implementation for a Forge V2 vertical.

This skill is bifurcated:

1. `plan` mode
2. `build` mode

Use `plan` mode when no build plan exists yet for the target vertical.
Use `build` mode when a build plan already exists and implementation should proceed.

Do not treat planning and implementation as unrelated. The output of planning must directly drive the build.

## Pre-Build Gate

`forge-build` is not the first skill to use on a new or newly deepened slice.

Before using this skill, the slice should already have:

1. a coherent schema pass from `forge-schema`
2. a consistency pass from `forge-review`
3. a security pass from `forge-security`

Use this skill before those checks only when the user is explicitly asking you to repair issues discovered by review or security work.

## Mode Selection

For the chosen vertical:

1. Check whether a build plan already exists.
2. If it does not exist, enter `plan` mode first.
3. If it exists, enter `build` mode.

If a build plan exists but is clearly incompatible with the current schema, repair the plan before building.

## Forge CLI First

When the Forge CLI exists, prefer it as the primary context and audit interface.

Use it for:

1. initializing a workspace or schema tree
2. retrieving scoped context for a vertical, runtime container, component, or flow
3. launching the audit surface for human inspection of audit artifacts

Expected commands:

- `forge init`
- `forge context`
- `forge audit`

Use `forge context` before planning or building a scoped task whenever it is the most efficient way to retrieve the relevant schema context.

If the CLI is not available yet, fall back to reading the schema artifacts directly.

## Plan Mode

Plan mode should:

1. Choose or confirm the target vertical.
2. Define the thinnest runnable end-to-end slice.
3. Break that slice into ordered build increments.
4. Define verification checkpoints for each increment.
5. Record meaningful planning decisions in `decision_notes.md`.

### Planning Rules

1. Plan vertically, not by technical layer.
2. Start with the smallest slice that proves the architecture.
3. Make deferrals explicit.
4. Do not add architecture just to make the plan look neat.
5. Draft the first plan, explain the reasoning, then let the user critique it.

### Planning Output

The plan should identify:

- chosen vertical
- first runnable slice
- ordered increments
- dependencies
- deferrals
- verification checkpoints

## Build Mode

Build mode should execute the approved plan incrementally.

### Build Workflow

For each increment:

1. Confirm the current increment goal.
2. Write or update tests first.
3. Implement the minimum code required to make the tests pass.
4. Simplify the implementation where needed without changing behavior.
5. Run the required verification.
6. Record important implementation decisions in `decision_notes.md`.
7. Move to the next increment only when the current one is green.

Do not batch large amounts of work without testing.

### Context Retrieval During Build

Before implementing a scoped task, retrieve the narrowest useful context.

Prefer:

1. `forge context` for the current vertical, container, component, or flow
2. direct schema reads only when CLI context is unavailable or insufficient

Do not implement from vague whole-repo context when a smaller scoped context can be retrieved.

### Sub-Agent Dispatch

Use sub-agents when the current build increment can be safely partitioned into independent work.

Good cases:

- backend container work and frontend container work with a stable contract
- one component implementation and another component implementation with disjoint ownership
- production code work and independent test harness work with clear interfaces
- parallel verification passes after implementation

Rules:

1. Do not dispatch sub-agents for the current blocking task if the main path needs immediate tightly coupled reasoning.
2. Give each sub-agent a disjoint ownership scope.
3. Give each sub-agent the relevant Forge CLI or schema context for its scope.
4. Do not ask sub-agents to redesign the architecture.
5. Review and integrate sub-agent output before moving on.

## Required TDD Workflow

Build mode must use a TDD-style cycle wherever behavior changes:

1. write a failing test
2. make it pass with the smallest reasonable implementation
3. refactor or simplify while keeping tests green

For bug fixes:

1. reproduce the bug with a failing test first
2. fix the bug
3. confirm the test passes

Never rely on "it looks right" as proof.

## Test Sandboxing Rule

Treat tests as a protected correctness boundary, not a flexible implementation companion.

Rules:

1. Write or extend tests before changing implementation behavior.
2. Do not rewrite tests just to make a broken implementation pass.
3. Only change an existing test when one of these is true:
   - the test encodes behavior that is genuinely wrong
   - the test contradicts the approved schema or build plan
   - the test is structurally flaky or invalid
   - the intended behavior has been explicitly changed and approved
4. If a test fails, prefer fixing the implementation first.
5. If a test appears wrong, explain why before changing it.
6. Keep test changes scoped to the behavior actually under construction.

Use this decision check before editing an existing test:

- Is the test wrong, or is the code wrong?
- Does the test contradict the approved architecture or vertical plan?
- Would a human reviewer believe this test edit improves correctness, rather than hiding a defect?

## Required Testing Levels

The build is not complete unless it is tested at all relevant levels.

### 1. Unit Tests

Use for:

- pure logic
- validators
- transforms
- component-local behavior
- service-level rules

### 2. Integration Tests

Use for:

- API boundaries
- persistence boundaries
- container-to-store interaction
- critical component interactions

### 3. Full-System Tests

Use for:

- real end-to-end execution of the vertical in the environment in which it is being built
- actual startup/run behavior
- real user or system flows

Do not stop at unit or integration coverage if the vertical can be exercised end to end.

### Full-System Test Rule

Always test the full system in the environment being built whenever that is feasible.

Examples:

- local build -> run and test locally
- dev environment build -> run and test in dev
- browser-facing vertical -> verify in the actual browser/runtime environment

The point is to prove the vertical works as a real system path, not just in isolated tests.

## Anti-Bloat Build Rules

1. Do not build horizontally.
2. Do not introduce speculative abstractions.
3. Do not create new shapes unless the schema or the build clearly requires them.
4. Do not broaden scope mid-increment.
5. Do not "clean up" unrelated code during a vertical build.
6. Prefer the simplest working implementation first.
7. Refactor only after behavior is proved by tests.

Use these challenge questions:

- Does this code change directly advance the current vertical slice?
- Can this be deferred without invalidating the slice?
- Is this abstraction earned yet?
- Is this test proving real behavior or just testing implementation detail?

## Review Rules During Build

For each increment, check:

1. the code still aligns with the schema
2. the build still follows the chosen vertical
3. the tests actually prove the changed behavior
4. the system still runs after the increment
5. complexity has not grown unnecessarily

If implementation reveals architectural drift, stop and route back:

- schema problem -> `forge-schema`
- consistency problem -> `forge-review`
- security issue -> `forge-security`

## Reference Skill Usage

This skill should use the coding-agent reference repo for specific workflows instead of duplicating them.

Before relying on that reference repo, always update it first:

```bash
git -C skills/forge-build/coding_agent_skills_reference pull --ff-only
```

Then consult the relevant skills under:

- `skills/forge-build/coding_agent_skills_reference/skills/`

Especially useful reference skills:

- `planning-and-task-breakdown`
- `incremental-implementation`
- `test-driven-development`
- `frontend-ui-engineering`
- `api-and-interface-design`
- `code-simplification`
- `browser-testing-with-devtools`
- `security-and-hardening`

Use them like this:

- planning work -> `planning-and-task-breakdown`
- incremental delivery discipline -> `incremental-implementation`
- test-first implementation -> `test-driven-development`
- frontend implementation quality -> `frontend-ui-engineering`
- backend/API contract and interface work -> `api-and-interface-design`
- reducing unnecessary complexity -> `code-simplification`
- browser/runtime verification -> `browser-testing-with-devtools`
- implementation hardening -> `security-and-hardening`

The Forge build logic stays here. The task-specific implementation technique comes from those reference skills.

## Audit Surface

When audit artifacts need human review, prefer the Forge CLI audit surface.

Expected command:

```bash
forge audit
```

The intended behavior is:

- spin up a local webserver
- render the available audit artifacts
- allow interactive inspection
- allow export of those artifacts

Use this surface for reviewable architecture outputs rather than forcing humans to inspect raw files when the audit interface is available.

## Decision Notes

Record meaningful build decisions in `decision_notes.md`, including:

- why a vertical was chosen first
- why a slice was considered thin enough
- what was deferred
- why a test strategy was chosen
- why a simplification or refactor was made
- any architectural issues discovered during build

## Constraints

1. Do not implement without a build plan.
2. Do not treat testing as optional.
3. Do not call a slice complete without full-system verification where feasible.
4. Do not silently reshape the architecture during implementation.
