---
name: forge-validate
description: >
  Forge post-implementation validation skill. Use after forge-build has completed to verify
  that the implementation actually behaves as the spec declares. Runs three phases: static analysis
  (code shape vs spec), test coverage (suite covers declared contracts), and behavioral
  (running system behaves as specified). Produces workbench/validation.md. Read-only — never
  modifies specs or implementation files.
  Triggers on: "validate the implementation", "check the build", "forge-validate", or any request
  to verify that generated code matches the Forge spec.
---

# forge-validate

Read `references/framework.md` before starting. Read `workbench/discovery.md` and `workbench/build-plan.md` for context on what was built.

## Purpose

Verify at three levels that implementation satisfies the spec. This skill is **read-only** — it surfaces findings for the human to act on, never modifies specs or code.

## Pre-conditions

- `forge validate` must exit clean (structural spec integrity).
- `workbench/build-plan.md` must exist and show all tasks as `done`.
- Source files referenced in the build plan must exist on disk.

If any pre-condition fails, report it and stop.

## Phase 1 — Static Analysis

Read source files and reason about whether they satisfy the element's spec contract. No code execution.

For each element, for each operation:

| Check | How |
|-------|-----|
| Input handling | Scan for field validation / parsing matching each declared `inputs` type field |
| Output shape | Scan all return paths for declared `outputs` type fields |
| Error coverage | Scan for error-return paths matching each entry in `raises` |
| Policy enforcement | Scan for auth checks / rate limit middleware where security policies apply |

Run `forge context <element-id>` to get the spec for each element being checked.

**Severity logic:**
- P1: Missing output field, missing required error-return path, missing auth check on a secured operation
- P2: Input field not validated, error returned that isn't in `raises`
- P3: Policy applied but mechanism unclear from code, minor output shape drift

### Phase 1 Output

For each element: `PASS`, `FAIL [list of checks]`, or `PARTIAL [passing checks / failing checks]`.

## Phase 2 — Test Coverage

Verify the test suite covers the declared contracts.

For each operation:
- Does a test exist that uses the exact `inputs` values from the spec's example cases?
- Does a test verify each declared output field?
- Does a test trigger each error in `raises`?
- For `command` and `async_command` operations: does a test verify the declared side effects?

For each flow:
- Does an integration test exist that exercises the full interaction chain?
- Does it run against live infrastructure (no internal mocks)?

**Check**: if a test uses placeholder values (`"user-1"`, `100`, `"test"`) rather than spec-derived values, flag it as P3.

**Severity logic:**
- P1: No test exists for an operation with a public contract
- P2: Test exists but doesn't verify a declared output or error
- P3: Test uses generic values instead of spec-derived values

## Phase 3 — Behavioral Verification

Start the system and verify runtime behavior matches the spec.

### System startup

Use the `packaging.runtime` and any `run_command` from the module to start the system. If no run command is documented in `workbench/discovery.md`, ask the human how to start it.

### Behavioral checks

For each operation with a public contract:
1. Send a request matching the spec's declared `inputs`.
2. Verify response matches declared `outputs` shape.
3. Verify declared errors are returned with correct HTTP status codes.

For side effects declared in operations (state writes, event emissions):
- Verify via logs or observable system state — not by reading implementation code.
- A side effect is `FOUND` only when confirmed by log evidence or observable state change.
- `UNVERIFIABLE` when the log location is unknown.
- `NOT FOUND` when logs are accessible but show no matching event.

For flows:
- Execute the full trigger-to-completion path.
- Verify postconditions are met.

**Severity logic:**
- P1: Operation returns wrong shape, wrong error code, or crashes
- P2: Side effect is `NOT FOUND` when expected
- P3: Side effect is `UNVERIFIABLE`, minor schema drift in response

## Output

Write `workbench/validation.md`:

```markdown
# Validation Report — <date>

## Summary
Phase 1 (Static): <PASS | FAIL | PARTIAL>
Phase 2 (Tests):  <PASS | FAIL | PARTIAL>
Phase 3 (Behavioral): <PASS | FAIL | PARTIAL | SKIPPED>

## Phase 1 — Static Analysis
[Per-element findings]

## Phase 2 — Test Coverage
[Per-operation findings]

## Phase 3 — Behavioral
[Per-operation + per-flow findings]

## Recommended Actions
[Grouped by severity: what to fix and which skill to route to]
```

## Routing Failed Findings

| Finding type | Route to |
|-------------|----------|
| Spec is wrong / incomplete | `forge-spec` to revise the element |
| Implementation doesn't match spec | `forge-build --resume <element-id>` |
| Test is wrong or missing | Re-dispatch `forge-build` subagent for that element |
| Behavioral failure (system bug) | Human investigation + `forge-build --resume` |

## Key Constraints

- Never modify spec files or implementation files.
- `UNVERIFIABLE` and `NOT FOUND` are distinct findings with different severity.
- A partial run that completes Phase 1 + Phase 2 but can't start the system is still valid — write the report for what ran.
- Phase 3 is skipped (not failed) if the system cannot be started; note the reason.
