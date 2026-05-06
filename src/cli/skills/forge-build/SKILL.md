---
name: forge-build
description: >
  Forge implementation orchestrator. Use when the spec is complete and reviewed (forge-review
  has run clean) and the user wants to generate working implementation code and tests.
  Writes a dynamic task list to workbench/build-plan.md, then dispatches subagents to implement
  each task using `forge context` to pull their own context from the CLI. Subagent granularity
  is determined dynamically based on system size. Orchestrator retries failures automatically
  before surfacing to the human.
  Triggers on: "implement this", "build the code", "forge-build", or any request to generate
  implementation from a complete Forge spec.
---

# forge-build

Read `references/framework.md` before starting. Read `workbench/discovery.md` for system context.

## Purpose

Orchestrate implementation of a complete, reviewed Forge spec. The orchestrator plans, dispatches subagents, tracks progress, and retries failures. Subagents are isolated — each one receives only a task ID and runs `forge context` to get everything it needs.

## Step 1 — System Assessment

Before writing anything:

```bash
forge list --kind element --ids-only   # enumerate all elements
forge list --kind module               # understand module boundaries
forge validate                         # must be clean before proceeding
```

If `forge validate` has errors, stop and tell the human to run `forge-review` first.

Count elements and determine task granularity:

| System size | Granularity |
|-------------|-------------|
| < 10 elements | module-level tasks (one subagent implements all elements in a module) |
| 10–40 elements | element-level tasks (one subagent per element) |
| > 40 elements | element-level tasks with parallel dispatch (multiple subagents concurrently) |

## Step 2 — Build Plan

Write `workbench/build-plan.md` before dispatching any subagents:

```markdown
# Build Plan — <date>

## System: <system-id>
## Granularity: <module | element>
## Total tasks: <N>

## Tasks

| ID | Target | Dependencies | Status | Attempts |
|----|--------|-------------|--------|----------|
| task_001 | <element-or-module-id> | [] | pending | 0 |
| task_002 | <element-or-module-id> | [task_001] | pending | 0 |
...

## Architecture Decisions
[Extract from workbench/discovery.md: language, runtime, framework, DI pattern, error handling style, test framework]
```

**Dependency ordering**: tasks whose target element has operations called by other elements must complete before their dependents. Use `forge inspect <id>` to discover caller/callee relationships. Tasks with no inter-dependencies can run in parallel.

Present the build plan to the human and get confirmation before dispatching.

## Step 3 — Subagent Dispatch

For each task in dependency order:

### Subagent prompt template

```
You are implementing a single unit of a Forge spec.

Target: <element-or-module-id>
Task ID: <task_id>

## Your context

Run this command to get your full implementation context:
  forge context <element-or-module-id> --format markdown

The output contains: the element with all properties and operations, parent module/domain/system,
all referenced types (transitive), errors, contracts, interactions, cascaded policies, and datastores.

## Architecture

<paste the Architecture Decisions section from build-plan.md>

## What to produce

For each operation in the element:
1. Tests first — write tests derived from the operation's declared inputs, outputs, errors,
   and any example/edge cases in the spec. Tests must be runnable and specific to the spec values.
2. Implementation — write the minimal code that satisfies the spec contract. No extra abstractions,
   no error handling beyond what's declared, no feature flags.

## Rules

- Implement exactly what the spec declares. Nothing more.
- Every output field declared in an operation must be present in the implementation.
- Every error declared in `raises` must have a corresponding error-return path.
- Integration tests (flows, interactions) must run against live infrastructure — no internal mocks.
- External third-party APIs (integrations) may be mocked with test credentials or sandbox environments.
- If the spec is ambiguous on a decision the architecture block doesn't resolve, report it as
  an `architecture_conflict` instead of guessing. Do not write files on conflict.

## Output

Write files to the paths implied by the module's `packaging.runtime` and the project's source structure.
Report: files written, tests passing, or architecture_conflict with the specific ambiguity.
```

### Tracking

After each subagent completes, update `workbench/build-plan.md`:
- Mark task as `done` with files written.
- On failure: increment attempts, note failure reason.

## Step 4 — Failure Handling

On subagent failure:
1. **Attempt 1 retry**: Re-dispatch the same subagent with the error reason appended to the prompt.
2. **Attempt 2 retry**: Re-dispatch with explicit guidance targeting the reported error.
3. **After 2 retries**: Surface to the human with the full failure reason. Ask whether to skip, fix the spec, or provide manual guidance.

On `architecture_conflict`:
- Do not retry. Surface immediately with the specific ambiguity.
- Ask the human to resolve it (add to `workbench/discovery.md` or update relevant spec files), then re-dispatch.

## Step 5 — Completion

When all tasks are `done`:
1. Run `forge validate` to confirm spec is still clean.
2. Provide a summary: modules implemented, files written, any skipped tasks.
3. Recommend running `forge-validate` to verify behavioral correctness.

## Key Constraints

- Do not dispatch subagents until `workbench/build-plan.md` is written and human-confirmed.
- Subagents never read other subagents' output files — isolation is strict.
- Orchestrator never writes implementation code directly — only subagents do.
- `forge validate` must pass before dispatch and should pass after completion.
