---
name: forge-build
description: "Lean Forge V4 build and QA workflow. Use when implementing a thin build slice from the Forge V4 model, scoping code-owned C3 annotations before development, or generating thorough black-box and structural tests from Forge crawl operation, component, container, runtime, and system contracts. Supports two modes only: C3 scope-and-develop, and QA testing."
---

# forge-build

Read before starting:

- `../../FRAMEWORK_V4.md`
- `../../SCHEMA_REFERENCE_V4.md`
- `../forge-schema/SKILL.md`
- `../forge-review/SKILL.md`
- `../forge-security/SKILL.md`

Prefer when available:

- `forge list`
- `forge context`
- `forge crawl --format json`
- `forge audit`

## Purpose

Build one thin Forge V4 slice while keeping implementation, tests, and code-owned C3 schema aligned.

This skill has two modes:

1. `develop`: scope the C3 work, implement the slice, and keep annotations crawlable.
2. `test`: act as a QA testing agent and generate focused tests from the V4 model.

Do not redesign the system here. If implementation proves the system, containers, entities, flows, or security posture are wrong, route the change back through `forge-schema`, `forge-review`, or `forge-security`.

## Decision Log

Read `forge/decisions.yaml` when it exists and use it as build context.

Record or request a decision entry for non-trivial implementation direction,
source-root or file layout choices, contract interpretation, testing strategy,
deferrals, accepted risk, or deviations from the reviewed Forge model. Use the
`forge.decisions` schema from `SCHEMA_REFERENCE_V4.md`.

Do not use decisions as a running journal. Record only choices that future build,
review, security, or schema work would need to understand.

## Forge V4 Structure

Forge V4 is structured as:

```text
forge/
  system.yaml       # C1 system intent, actors, dependencies, business actions
  containers.yaml   # C2 runtime containers, source roots, runtime flows
  entities.yaml     # business state, canonical data refs, ownership, persistence
  decisions.yaml    # crawlable decision records
  crawler.yaml      # crawler file/comment configuration when customized
```

Code owns C3 through annotations placed beside the implementation:

```text
@forge:component
@forge:type
@forge:persistence
@forge:operation
```

Central schema describes system and container intent. Code annotations describe the component, operation, type, and persistence reality.

## Crawlable Layout

Directory layout is identified by `containers[].source_root` in `forge/containers.yaml`.

Rules:

1. Every runtime container that owns code should declare a `source_root`.
2. Architecture-significant code for that container should live under its `source_root`.
3. The crawler scans declared source roots, then extracts supported `@forge:*` annotations from supported comment styles.
4. An annotation can omit `container` when the file is under a matching `source_root`.
5. Files outside declared source roots are not part of the crawled C3 model.
6. If new implementation must live outside the current roots, update the container `source_root` or add the correct container before building.
7. Follow the repository's local folder conventions inside each source root; do not invent a new universal Forge folder taxonomy.

Place annotations close to the code that owns the truth:

- interface component: route, screen, worker, CLI, scheduler, event boundary, or meaningful nested surface
- logic component: service, module, domain logic, orchestration unit
- persistence component: repository, store, database adapter, file adapter
- datastore component: database-facing implementation where the store itself owns behavior
- type: data contract, DTO, model, schema, event shape, persisted record
- operation: function, method, handler, command, or workflow step that performs behavior

The low-level code is the schema. If code participates in a runtime or container flow, its `@forge:operation` contract must describe `input`, `returns`, `logic`, and where it participates.

## Mode Selection

Use `develop` when the user wants implementation or C3 scoping for a build slice.

Use `test` when the user wants a QA pass, test plan, generated tests, or stronger validation coverage.

If the user does not name a mode, choose the smallest mode that satisfies the request.

## Develop Mode

Develop mode scopes and builds one thin slice.

Before coding:

1. State assumptions explicitly.
2. If multiple interpretations exist, present them instead of choosing silently.
3. If a simpler approach exists, say so and prefer it unless it violates the Forge model.
4. If the request, schema, or code context is unclear, stop and name the ambiguity.
5. Define success criteria as verifiable checks before implementation.

Workflow:

1. Load the narrow Forge context for the target business action, container flow, container, entity, or component.
2. Identify the smallest runnable slice and the runtime steps it touches.
3. Map each touched runtime step to the C3 annotations it needs.
4. Confirm all implementation files live under the correct `source_root`; adjust schema only when the source-root model is genuinely wrong.
5. Implement the minimum code needed for the slice.
6. Add or update C3 annotations in the same code change.
7. Add or update focused tests.
8. Run relevant tests and `forge crawl --format json`.
9. Fix broken references, missing annotations, contract drift, and failed tests before calling the slice complete.

The C3 scope map should identify:

- containers and source roots touched
- components to create or update
- operations to create or update
- `@forge:type` contracts used as operation inputs and returns
- persistence annotations touched
- container flow step references such as `create_note:2`
- local flow step references such as `create_note_backend:1`
- security or review findings that must be resolved during the build

### Develop Guardrails

Bias toward caution over speed.

Think before coding:

- do not assume hidden requirements
- do not hide confusion
- surface tradeoffs when the implementation path is not obvious
- ask only when ambiguity blocks a responsible implementation

Keep the implementation simple:

- build no features beyond the selected slice
- add no abstractions for single-use code
- add no configurability that was not requested
- add no defensive error handling for impossible states unless required by the Forge contract
- if the implementation grows much larger than the behavior warrants, simplify it before moving on

Make surgical changes:

- touch only files required by the slice, tests, and C3 annotations
- do not improve adjacent code, comments, formatting, or naming unless the current change requires it
- match existing repository style even when another style is personally preferable
- remove only imports, variables, functions, files, or annotations made unused by the current change
- mention unrelated dead code or stale schema separately instead of deleting it

Drive execution by verifiable goals:

- convert each build task into a checkable success criterion
- for validation work, write or update tests for invalid inputs before calling the validation complete
- for bug fixes, reproduce the bug with a failing test before fixing it when feasible
- for refactors, establish current behavior before changing structure and verify behavior afterward
- for multi-step slices, use a short plan where each step has its own verification command or observation

## Test Mode

Test mode is a thorough QA agent. All test documentation, test planning, and black-box test implementation must be sourced from `forge crawl --format json` plus scoped Forge context.

Do not inspect implementation details to decide expected behavior unless the user explicitly asks for white-box structural tests. For normal QA, the source of truth is the Forge model: business actions, system context, container flows, component/local flows, entities, data shapes, persistence refs, and `@forge:operation` contracts.

### Test Source Rules

1. Start by loading `forge crawl --format json`.
2. Use implementation files only to locate callable entry points, selectors, test harness setup, and existing test conventions.
3. Derive expected behavior from Forge contracts, not from current implementation behavior.
4. Treat implementation behavior that contradicts Forge contracts as a defect unless the Forge model is clearly stale.
5. Use white-box structural tests only for internal branching, coverage gaps, unreachable paths, or explicit user requests.
6. Label white-box tests as structural so they are not confused with contract tests.

### Test Case Derivation

For every selected operation, component flow, container flow, runtime flow, and business action, derive a test matrix before writing tests.

Include:

- valid nominal inputs from the referenced data shape
- multiple valid boundary inputs
- invalid but well-formed inputs
- malformed inputs with missing, extra, null, wrong-type, or wrongly nested fields
- fuzzed strings, numbers, dates, identifiers, arrays, and nested objects where applicable
- security-relevant adversarial inputs from `forge-security` context
- branch-triggering inputs for every declared condition
- persistence edge cases for reads, writes, duplicate records, missing records, and ownership rules
- retry, timeout, empty-state, error-state, and partial-failure cases when implied by the flow

Each test case must identify:

- Forge source reference: operation id, component id, container flow step, local flow step, entity, or business action
- input shape and exact example payload
- expected output, state change, UI state, emitted call, or error
- test level
- whether it is black-box contract, structural white-box, security, fuzz, or regression

### Naming

Name every test case with this pattern:

```text
test<MethodName>_<scenario>_<expectedResult>
```

Rules:

1. `test<MethodName>` uses camel case after the `test` prefix.
2. `scenario` is lower snake case.
3. `expectedResult` is lower snake case.
4. The name must reveal the Forge behavior being tested.
5. Examples: `testCreateNote_validDraft_returnsCreatedNote`, `testCreateNote_missingTitle_returnsValidationError`, `testRegisterUser_duplicateEmail_returnsConflict`.

### Test Levels

Generate tests in this order:

1. Unit tests: black-box operation tests for `input`, `returns`, and declared `logic`.
2. Component tests: black-box local-flow tests for operation ordering, `passes`, state shaping, and component responsibilities.
3. Container tests: integration tests for all operations inside a runtime container step.
4. Runtime flow tests: cross-container tests for trigger, step handoffs, branches, outputs, and outcomes.
5. Full system tests: business-action tests against real interfaces or realistic runtime boundaries.
6. Structural tests: white-box tests only where branch coverage, unreachable states, or internal invariants cannot be proven through black-box tests.

Logical files should mirror the test level and Forge scope. Prefer names such as:

```text
tests/unit/<operation_or_component>_test.*
tests/component/<component_or_local_flow>_test.*
tests/integration/<container_or_container_flow>_test.*
tests/system/<business_action_or_runtime_flow>_test.*
tests/e2e/<business_action>_test.*
tests/reports/
```

Follow existing repository conventions when they already define equivalent folders.

### Test Structure

Every test must follow Arrange, Act, Assert.

Rules:

1. Arrange creates all required data, configuration, mocks, services, browser state, auth state, and fixtures.
2. Act performs exactly the operation, flow, user action, API call, CLI command, or system trigger under test.
3. Assert verifies the declared Forge contract: output, state change, UI state, persisted result, emitted call, error, branch, or outcome.
4. Keep setup inside fixtures, factories, containers, test harnesses, or explicit test helpers.
5. Do not require manual environment setup, hand-edited config, preloaded database state, manual login, manual browser clicks, or human sequencing.
6. Smoke and full-system tests must be autonomously runnable from a documented command.
7. If a full-system test needs services, databases, seeded users, credentials, queues, files, or browsers, the test suite must provision, seed, reset, or mock them itself.
8. If true autonomous setup is impossible, mark the gap in the audit report and do not claim full-system coverage.

### Contract Continuity

For every flow under test, prove that data flows correctly.

Check:

- trigger input matches first runtime step input
- each runtime step output matches the next step input
- branch conditions are reachable and mutually understandable
- branch outputs match branch target inputs
- terminal outputs match declared outcomes
- operation inputs and returns match referenced `@forge:type` shapes
- local flow `passes` values match the next local step input
- persisted writes satisfy entity ownership and persistence refs
- reads return shapes that can feed downstream operations

If a value appears, disappears, changes shape, crosses a trust boundary, or changes owner without an explicit Forge handoff, create a failing test or a review finding.

### UI And Full-System Automation

When the system has a real interface, implement autonomous end-to-end tests against that interface.

For web apps, prefer Playwright unless the repository already uses another equivalent browser framework.

E2E tests should:

- drive the same user actions implied by Forge business actions
- use real selectors and accessible roles where possible
- submit valid, invalid, malformed, and fuzzed inputs through the UI
- click primary controls, keyboard-submit forms, and test focus/blur behavior
- test edge interactions such as button-edge clicks, double clicks, rapid submits, disabled controls, back/forward navigation, refresh, and viewport changes when relevant
- assert visible UI states, network calls, persisted outcomes, and error handling from the Forge contract
- capture screenshots, traces, videos, or logs when the framework supports it

For non-web systems, use the closest real interface: CLI commands, API clients, queues, files, scheduled jobs, desktop UI automation, or service calls that match the declared trigger.

### Reports And Logs

Every thorough QA pass should produce auditable output.

Prefer repository-native reporting when available. Otherwise create or update a report under an existing reports directory or `tests/reports/`.

The report should include:

- Forge crawl timestamp or command used
- targeted business actions, flows, containers, components, and operations
- generated test matrix
- test files created or updated
- black-box versus structural test classification
- fuzz and malformed input strategy
- full-system automation coverage
- commands run
- pass/fail results
- unresolved gaps and reasons

Keep reports factual and reproducible. Do not handwave coverage.

## Build Guardrails

1. Build one thin slice at a time.
2. Keep code under declared source roots so the crawler can see the C3 model.
3. Do not add architecture-significant code without a nearby Forge annotation.
4. Do not silently reshape central C1/C2 schema during implementation.
5. Do not broaden a container flow because a local operation flow needs detail; local/container flow detail belongs in C3 annotations.
6. Do not change unrelated code or tests.
7. Do not rewrite tests merely to match broken implementation.
8. Prefer the repository's existing structure, naming, tools, and test patterns.

## Completion

A build or QA pass is complete only when:

- relevant tests pass
- `forge crawl --format json` succeeds
- code-owned C3 annotations are present for the touched architecture-significant code
- operation inputs and returns line up across local, container, runtime, and system flow boundaries
- review and security obligations for the slice are resolved or explicitly handed back to the proper skill
