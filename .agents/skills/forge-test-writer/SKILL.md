---
name: forge-test-writer
description: >
  Use this skill when the forge-implement orchestrator dispatches a
  test-writing task for a Forge spec entity (atom, flow, or journey).
  This skill is not typically invoked by a human directly — it is a
  subagent skill. Takes an entity id + test level (unit | integration |
  system) + target test file paths from the orchestrator. Loads the
  spec via forge context, generates exhaustive contextual tests per the
  entity's verification block and declared invariants, side effects,
  failure modes, and logic branches. Writes test file(s) plus a sibling
  .audit.md file mapping every spec requirement to its tests. Blind to
  implementation — never reads existing implementation files.
---

# forge-test-writer

Subagent dispatched by `forge-implement` to generate tests for one Forge entity (atom / flow / journey) at one test level (unit / integration / system). You read the spec via `forge context`, generate tests, write the audit file, and exit.

Load `references/framework.md` when you need to make judgment calls about live-vs-mock, domain value sourcing, or exhaustiveness vs. minimality.

## Inputs (from orchestrator)

- `entity_id` — atom id (`atm.mod.name`), flow id (`flow.name`), or journey id (`jrn.name`)
- `level` — `unit` | `integration` | `system`
- `target_test_file` — absolute path where tests are written
- `target_audit_file` — absolute path where the audit md is written
- `architecture` — block from `supporting-docs/implementation-plan.yaml` (test framework, language, styling, etc.)

## Non-negotiables

1. **Never read implementation files.** Never open `target_source_file`, never look at sibling implementations. Your source of truth is the spec alone.
2. **Contextual, not generic.** Use domain values from the spec (real field names, real error codes, real constants). Never `"foo"` / `"test@example.com"` / `42` when the spec has concrete values to use.
3. **Exhaustive.** Cover every declared `example_case`, `edge_case`, `property_assertion`, `failure_mode`, every `logic` branch, every `invariant.pre`, every `invariant.post`, and verify every `side_effect` marker.
4. **Auditable.** Strict test naming, linking comments, mirrored describe-blocks, and a `<entity>.audit.md` file.
5. **Stop after write.** Do not also implement. Do not modify the spec. Do not touch other files.

## Step 1 — Load context

```bash
forge context <entity_id> --spec-dir <spec-dir>
```

Parse the bundle. For an atom: read spec (input, output, side_effects, invariants, logic, failure_modes), verification (property_assertions, example_cases, edge_cases), and the L0 slice (types, errors, constants). For a flow: read sequence, transaction_boundary, verification_criteria. For a journey: read handlers, transitions, exit_states, verification_criteria.

Read the architecture block the orchestrator passed. Note the test framework, language, idiomatic patterns.

## Step 2 — Generate tests

### Test style selector by kind / level

| Entity | Level | Styles |
|---|---|---|
| PROCEDURAL atom | unit | unit tests + contract tests (for each `CALL <atom>`) + property-based tests (for meaty invariants only) |
| DECLARATIVE atom | unit | unit tests + golden-file tests (output matches committed golden) |
| COMPONENT atom | unit | unit tests + snapshot tests + user-event simulation |
| MODEL atom | unit | unit tests + bounds verification + fallback-triggered tests |
| Flow | integration | live system started via L5 ops `run_command`; real HTTP/CLI/worker/event invocations against the running service; only genuine third-party external APIs mocked |
| Journey | system | full E2E against live system; browser / CLI / API client drives all transitions; no internal mocks |

### Live system startup (integration and system levels)

For `level: integration` (flows) and `level: system` (journeys), tests run against a live instance of the system — not mocked internals.

**Startup lifecycle.** Read from `L5_operations.yaml`:
- `run_command` — how to start the system
- `port` — where it listens
- `health_check_path` — readiness probe (default `/health`)
- `readiness_timeout` — how long to wait (default 30s)

Generate `beforeAll` / `afterAll` (or language-equivalent `setup`/`teardown`) that:
1. Start the system via `run_command` as a subprocess
2. Poll the health endpoint every 2s until 200 OK or timeout
3. Set `BASE_URL` / connection handle used by all tests in the file
4. On teardown: terminate the subprocess cleanly

If `L5_operations.yaml` has no `run_command` or `port`, include a `TODO` comment and a `beforeAll` that asserts `TEST_BASE_URL` env var is set — so the developer can provide an already-running system.

**Surface-specific test style.** Generate live tests appropriate to the entry point kind declared in the L2 module's `interface.entry_points`:

| Entry point kind | Test approach |
|---|---|
| `api` (HTTP REST) | HTTP client tests — `supertest` (Node), `httpx` / `requests` (Python), `net/http/httptest` (Go). Make real HTTP calls to `BASE_URL`. Assert exact status codes and response bodies field-by-field. |
| `cli` | Subprocess invocation — `child_process.execSync` (Node), `subprocess.run` (Python), `exec.Command` (Go). Capture stdout, stderr, exit code. Assert exact output patterns from spec's `example_cases`. |
| `event_consumer` | Publish an event to the real broker / queue (or an in-process test broker compatible with the project's stack). Assert side effects: DB rows written, outgoing events emitted, log patterns matched. |
| `scheduled` | Invoke the scheduler entry point directly or trigger the job function via the exposed management API. Assert completion state and side effects. |
| `grpc` | Generated gRPC client for the target service. Make real RPC calls against the running server on `port`. |
| `web_journey_entry` | Browser automation (Playwright / Cypress / Selenium) or scripted HTTP session. Drive all journey transitions step by step against the live system. |
| `websocket` | WebSocket client. Connect, send messages, assert received events in order. |

**No internal mocks at integration/system level.** Do NOT mock internal atoms, modules, databases, caches, or message buses. Every internal dependency must run live. The only acceptable mocks are:
- Genuine third-party external APIs declared in `L0.external_schemas` (e.g., Stripe, Twilio) — use their test-mode credentials or a local fake (e.g., Stripe CLI local webhook server, Wiremock)
- Hardware/device dependencies that cannot be simulated in CI

**Behavioral chain requirement.** For each `example_case` at integration or system level, the test must exercise the complete input → processing → observable outcome chain. A test that only asserts the response shape without verifying side effects is incomplete:
- For API tests: send the request, assert response body AND verify the side effect (DB row exists, event emitted, external call made with correct args).
- For CLI tests: run the command with real args, assert stdout/stderr AND verify any filesystem or DB changes the command makes.

### Mandatory coverage (per atom)

Generate one test per each:
- `verification.example_cases[*]` entry
- `verification.edge_cases[*]` entry
- `verification.property_assertions[*]` entry
- `failure_modes[*]` entry
- Each distinct `WHEN` / `TRY` branch in the atom's `logic`
- Each `invariants.pre[*]` expression (test that tripping the pre-condition produces the expected error)
- Each `invariants.post[*]` expression (test that the post-condition holds after a success case)
- Each `side_effects` marker:
  - `WRITES_DB` → test asserts the relevant datastore has the expected row after the call
  - `EMITS_EVENT` → test captures emitted events, asserts event name + payload shape
  - `CALLS_EXTERNAL` → test asserts the external schema's operation was invoked with expected args (via the mocked external service)
  - `READS_DB` / `READS_CACHE` / `READS_ARTIFACT` → test provides the dependency via mock, asserts it was consulted
  - `READS_CLOCK` → test injects a frozen time, asserts time-dependent behavior
  - `EMITS_EVENT` → see above

### Naming policy

Test names follow strict pattern: `test_<level>_<source>_<short_desc>`. Examples:
- `test_unit_example_case_happy_path`
- `test_unit_edge_case_concurrent_creation`
- `test_unit_failure_mode_PAY_VAL_001`
- `test_unit_branch_returns_existing_on_duplicate_key`
- `test_unit_invariant_post_row_exists_in_charges`
- `test_unit_side_effect_emits_payment_completed`

For languages where snake_case is not idiomatic (TypeScript, JavaScript), use the language-native equivalent (camelCase) while preserving the structure.

### Linking comments

Every test has a comment above it linking to the spec element it derives from:
```typescript
// Derived from atm.pay.charge_card.verification.example_cases[0]
test("test_unit_example_case_happy_path", async () => { ... });
```

### Describe-block structure

Organize tests into describe blocks mirroring the spec's sections:
```typescript
describe("atm.pay.charge_card", () => {
  describe("verification.example_cases", () => { /* ... */ });
  describe("verification.edge_cases", () => { /* ... */ });
  describe("verification.property_assertions", () => { /* ... */ });
  describe("failure_modes", () => { /* ... */ });
  describe("logic.branches", () => { /* ... */ });
  describe("invariants.pre", () => { /* ... */ });
  describe("invariants.post", () => { /* ... */ });
  describe("side_effects", () => { /* ... */ });
});
```

### Fixtures and types

Use shared fixtures and types from the scaffolding the orchestrator generated at run start. Do not redefine types inline. Reference them via imports that match the architecture's scaffolding paths.

### Domain values — non-negotiable

Test inputs must come from the spec's concrete values where available. Examples:
- `verification.example_cases[0].input.customer_id: "c_123"` → use `"c_123"` in that test, not `"user-1"`.
- An invariant references `const.MAX_CHARGE_CENTS` → use `const.MAX_CHARGE_CENTS` (via import), not the literal 10000000.
- A failure_mode returns `PAY.VAL.001` → assert the exact code, not a generic "error" assertion.

## Step 3 — Write the audit file

At `target_audit_file`, write a markdown table mapping every spec element to its test(s):

```markdown
# Audit: <entity_id> (<level> tests)

## Spec coverage matrix

| Spec element                          | Location                       | Test(s)                                             |
|---|---|---|
| example_cases[0] "happy path"         | verification                   | test_unit_example_case_happy_path                   |
| failure_modes[0] PAY.VAL.001          | failure_modes                  | test_unit_failure_mode_PAY_VAL_001                  |
| side_effect WRITES_DB                 | side_effects                   | test_unit_side_effect_writes_charges_table          |
| ...                                    | ...                            | ...                                                  |
```

Every row in the matrix must have at least one test name. If any spec element has no test, that's a bug in this skill's output — the skill should not exit.

## Step 4 — Report to orchestrator

Return a summary:
```
test_file:    <path>
audit_file:   <path>
tests_count:  <N>
coverage_matrix_rows: <M>
framework:    <name>
```

Do nothing else. Do not run the tests (orchestrator does that). Do not write implementation. Do not modify the spec.

## Gotchas

- If the spec has no `verification` entries, still generate tests from `logic` branches + `failure_modes` + `invariants` + `side_effects`. Flag the thin verification in the summary.
- If a `CALL <other_atom>` references an atom that doesn't exist yet, the contract test for that call mocks the called atom with its declared signature (from `forge inspect <called_atom>`). If inspect returns no match, skip the contract test for that call and include a note in the audit file.
- If `side_effects` contains a marker not in the mandatory-coverage list above (e.g., `PURE`, `IDEMPOTENT`), no side-effect test is needed for it.
- Do NOT generate tests that verify the atom's implementation approach. Tests verify the atom's CONTRACT (input → output, invariants, side effects). The implementation is free to use any approach.
- If the test framework is not inferable from architecture or `tech_stack.frameworks`, stop and return a failure: the orchestrator will handle re-architecture.
- **Domain values are non-negotiable at all levels.** A test that uses `"test@example.com"` when the spec has `example_cases[0].input.email: "alice@acme.com"` is a quality failure. Before writing, scan all generated tests: any placeholder that doesn't come from the spec is a bug in this skill's output.
- **Live system tests must poll for readiness.** Never send the first request immediately after starting the subprocess — always include a readiness polling loop in `beforeAll`. An unready system produces misleading failures.
- **CLI tests must capture both stdout AND stderr.** A CLI that writes error output to stderr and exits 1 is correct behavior — don't just check exit code 0; assert the specific output pattern declared in the spec's `failure_modes`.
- **Integration/system tests must not share startup state across test files.** Each test file gets its own `beforeAll`/`afterAll` lifecycle. Cross-file shared state causes flaky tests and obscures the source of failures.

## forge CLI commands used

| Command | Used for |
|---|---|
| `forge context <entity_id>` | Step 1 context load |
| `forge inspect <called_atom>` | Get signature of called atoms for contract test mocks |
