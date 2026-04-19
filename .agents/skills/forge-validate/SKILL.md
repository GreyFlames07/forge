---
name: forge-validate
description: >
  Use this skill when the user wants to validate that an implemented system
  matches its Forge spec corpus — checking source code against contracts,
  running the test suite mapped back to spec elements, and firing live
  synthetic probes against the running system. Activates on phrases like
  "validate the implementation", "check the system against specs", "run
  forge-validate", "verify live behaviour", or after forge-implement
  completes. Produces a validation report in chat and persists it as
  <spec-dir>/validation-report.md.
---

# forge-validate

Post-implementation validator. You read the spec corpus, read the implementation, run the test suite, start the system if it is not already running, fire synthetic probes derived from L3 contracts, and compare results — exact for output contracts, LLM-reasoned for implied behavioral logic, log-verified for side effects. You produce a report in chat and write it to `<spec-dir>/validation-report.md`.

You never modify specs or implementation. You never retry failed live probes. You always write the report, even on a partial run.

## Non-negotiables

1. **Read-only.** Never modify a spec file or source file.
2. **Exact contract assertion.** Response shapes must match L3 `output` schema field-by-field — no partial matching.
3. **Behavioral assertion is LLM-reasoned with explicit rationale.** Load full spec context, reason from it, state the reasoning in the report. Never emit PASS/FAIL without a rationale sentence.
4. **Side effects require log evidence.** Do not mark a side effect `FOUND` without a matching log line or query result.
5. **System startup is gated.** Only start the system if it is not already reachable. Never start it twice.
6. **Scope determines targets.** Full project by default; `--scope` limits to a module or single atom.
7. **Report is always written.** Even on partial runs, write what completed, mark the rest SKIPPED.

## Invocation flags

| Flag | Effect |
|---|---|
| `/forge-validate` | Full project — all four phases |
| `--scope <module_id\|entity_id>` | Limit scope to one module or atom |
| `--url <base_url>` | Use an already-running system — skip startup |
| `--skip-static` | Skip Phase 1 (static analysis) |
| `--skip-tests` | Skip Phase 2 (test suite) |
| `--skip-live` | Skip Phase 3 (live interactions) |
| `--skip-observability` | Skip Phase 4 (SLA + metrics check) |
| `--spec-dir <path>` | Override spec dir resolution |

## Workflow

### Step 1 — Load context

1. Resolve spec dir: `--spec-dir` flag > `$FORGE_SPEC_DIR` > auto-discover (walk upward for `.forge/`).
2. Load `implementation-plan.yaml` from the spec dir — needed for source file mapping, test command, and audit matrix locations.
3. Determine scope. Full project by default. With `--scope <id>`: if `<id>` contains no `.` treat as module prefix; else treat as exact entity id.
4. Enumerate targets: `forge list --kind atom --ids-only --spec-dir <dir>`. Filter by scope.
5. Announce: *"forge-validate: N atoms in scope. Running phases: static analysis → test suite → live interactions."*

---

### Step 2 — Phase 1: Static analysis

For each atom in scope:

1. Load full spec: `forge context <id> --spec-dir <dir>`.
2. Locate source file via `implementation-plan.yaml` `units[id].target_files`. If absent: record `source_missing` finding, skip atom.
3. Read the source file.
4. Check:
   - **Input handling** — does the code accept and validate every field declared in L3 `input`? Flag: undeclared fields accepted (WARN), declared fields unhandled (FAIL).
   - **Output shape** — does every code path that succeeds return all fields in L3 `output`? Flag missing required fields (FAIL), extra undeclared fields (WARN).
   - **Failure modes** — for each entry in `failure_modes`, is there a code path that returns the declared `error_code`? Flag any missing (FAIL). Flag if the code returns the right code but wrong HTTP status (WARN).
   - **Side effects** — for each `side_effects` marker, is there a backing code pattern (DB write call, event emit, log statement, external call)? Flag absent (FAIL).
5. Record per-atom: `PASS` / `WARN` / `FAIL` with specific gap descriptions.

Emit running tally after each module completes: *"Static: [PAY] 8 PASS, 1 WARN, 1 FAIL."*

---

### Step 3 — Phase 2: Test suite

1. Read test command from `implementation-plan.yaml` `architecture.test_frameworks`. If ambiguous, ask the user once.
2. Run the full test suite. Capture per-test pass/fail and overall coverage if available.
3. Load forge-test-writer audit matrices. Path per unit: `implementation-plan.yaml` `units[id].audit_file`. Skip units with no audit file (note them).
4. For each failing test: map test name to spec element via the audit matrix row. Record `entity_id`, `spec_element`, test name, failure message.
5. For each spec element with no audit matrix row: record `uncovered` finding.
6. Emit: *"Test suite: X passed, Y failed. Z spec elements have no test coverage."*

---

### Step 4 — Phase 3: Live interactions

#### 4a — System startup

1. Read L5 ops spec for `run_command`, `port`, `health_check_path` (default `/health`), `readiness_timeout` (default 30s).
2. If `--url <base>` provided: set `BASE_URL = <base>`, skip startup entirely.
3. Else: probe `http://localhost:<port>/<health_check_path>`. On 200: system already up, set `BASE_URL`, record "system found running".
4. Else: run `run_command` as a background subprocess. Poll health endpoint every 2s up to `readiness_timeout`. On success: set `BASE_URL`. On timeout: record `startup_failed`, mark Phase 3 `SKIPPED`, skip to Step 5.
5. If L5 ops spec has no `run_command` or `port`: ask the user: *"L5 ops spec does not declare a run command. Provide `run_command` and `port`, or pass `--url <base>` to use an already-running system."*

#### 4b — Probe generation and execution

For each atom in scope — skip atoms with `kind: DECLARATIVE`:

**Happy path probe:**
- Construct a valid request from L3 `input` schema. Use `example` field values if present; otherwise infer minimal valid values from declared types and constraints.
- Derive HTTP method and route from L2 module routing conventions or atom `side_effects` patterns. If genuinely ambiguous for more than one atom: ask the user once with a table of all ambiguous atoms.
- Fire the call against `BASE_URL`. Capture: status code, response body, response headers, latency (ms).

**Exact contract assertion:**
- Compare response body to L3 `output` schema field-by-field.
- Required field absent → `FAIL`.
- Wrong type → `FAIL`.
- Extra undeclared field → `WARN`.
- Status code not in declared success codes → `FAIL`.

**Behavioral assertion (LLM-reasoned):**
- Only run if contract assertion passed (malformed response makes behavioral reasoning undefined).
- Load full spec context. Reason: does the response honour what the spec implies beyond the explicit schema? Consider:
  - Idempotency — re-fire the same call. Expect the same result if the spec implies idempotency.
  - Ordering — if the spec implies a sequence or state machine, probe transitions in order and out of order.
  - Invariants — if the spec implies a business rule (e.g. balance cannot go negative), probe the boundary.
  - Consistency — if the spec says an entity is created, probe a read immediately after and verify it exists.
- State the reasoning explicitly. Mark `PASS` / `WARN` / `FAIL` with a rationale sentence.

**Failure mode probes:**
- For each entry in `failure_modes`: construct a request that triggers the declared `trigger` condition.
- Fire the call. Assert:
  - Response body contains the declared `error_code`.
  - HTTP status is appropriate for the error class (4xx for client errors, 5xx for server errors).
- Record PASS / FAIL per failure mode.

**Side effect verification:**
- After each probe: read system logs from the subprocess stdout/stderr (or from `log_file` path in L5 ops if declared).
- For each `side_effects` marker on the atom: search logs for a pattern matching the marker name, event name, or a declared log line pattern.
- Outcomes: `FOUND` (log evidence present) / `NOT FOUND` (no evidence — FAIL) / `UNVERIFIABLE` (log location unknown — WARN, note it).

Emit progress after each atom: *"Live: [atm.pay.charge_card ✓] [atm.pay.refund ✗ contract] ..."*

#### 4c — System teardown

If forge-validate started the system (not already running on entry): terminate the subprocess after all probes complete. Log: *"System stopped."*

---

### Step 5 — Phase 4: Observability check

Only runs if `observability` is present in `L5_operations.yaml`. Skip silently otherwise.

1. **Resolve SLA per atom.** For each atom in scope: look up module SLA in `observability.modules.<MODULE_ID>.sla`, then check `atom_overrides.<atom_id>.sla`. Atom override wins if present; else module SLA; else `observability.defaults`.

2. **SLA assertion from live probe timings.** For each atom that ran a live probe in Phase 3:
   - Compare recorded `latency_ms` against resolved `latency_p99_ms`. Strictly: if the single probe latency exceeds the declared p99, record `WARN` (one sample can't confirm a p99 violation, but it is a signal). State this caveat in the report.
   - Compare probe error responses against `error_budget_percent`. For this purpose, a single failed probe is treated as 100% error rate for that atom — record `FAIL` if the atom's error budget is > 0% and the probe returned an error response.

3. **Metrics presence check.** If the system exposes a `/metrics` endpoint (Prometheus format): scrape it and verify each declared metric name in `observability.modules.<MODULE_ID>.metrics` exists with the correct label set. Record `PASS` / `FAIL` per metric.

4. **Alert rules syntax check.** For each alert in `observability.modules.<MODULE_ID>.alerts`: verify `expr` is syntactically valid PromQL. This is a static check — does not require a running Prometheus instance. Record `PASS` / `WARN` (warn on unknown metric references in the expr that aren't declared in the same module's `metrics` block).

Emit: *"Observability: SLA assertions N atoms, metrics presence N metrics, alert syntax N rules."*

---

### Step 6 — Report

Generate the report in chat, then write to `<spec-dir>/validation-report.md`. Include a Phase 4 section if observability was checked.

```markdown
# Validation Report — <project> — <ISO timestamp>

## Summary

| Phase | Status | Pass | Warn | Fail |
|---|---|---|---|---|
| Static analysis | PASS/FAIL/SKIPPED | N | N | N |
| Test suite | PASS/FAIL/SKIPPED | N | — | N |
| Live interactions | PASS/FAIL/SKIPPED | N | N | N |
| Observability | PASS/FAIL/SKIPPED | N | N | N |

**Overall: PASS / FAIL / PARTIAL**

Scope: <full project | module <id> | atom <id>>
Spec dir: <path>
System: <base_url | SKIPPED — startup failed | SKIPPED — --skip-live>

---

## Phase 1 — Static Analysis

### <entity_id> — PASS / WARN / FAIL
- Input handling: PASS
- Output shape: FAIL — field `amount_settled` missing from implementation
- Failure modes: WARN — `PAY.INSUF.001` path present but returns 500, spec implies 402
- Side effects: PASS

...

## Phase 2 — Test Suite

Test command: `<command>`
Results: X passed, Y failed
Coverage: line Z% (if available)

### Failing tests mapped to spec

| Test | Spec element | Failure |
|---|---|---|
| test_charge_negative | `failure_modes[0]` trigger `amount <= 0` | AssertionError: expected PAY.VAL.001 |

### Uncovered spec elements

- `<entity_id>` → `<spec_element>` — no audit matrix row

## Phase 3 — Live Interactions

System: <BASE_URL> (<started by forge-validate | already running | --url provided>)

### <entity_id>

#### Happy path
- Input: `{...}`
- Response: <status> `{...}`
- Contract: PASS / FAIL — <gap description>
- Behavioral: PASS / FAIL — <rationale>

#### Failure mode: <name> (<error_code>)
- Trigger input: `{...}`
- Response: <status> `{...}`
- Contract: PASS / FAIL

#### Side effects
| Marker | Evidence | Status |
|---|---|---|
| `EVENT_NAME` | `log line text` | FOUND |
| `DB_WRITE` | no matching log pattern | NOT FOUND — FAIL |

---

## Next steps

- FAIL items: [list entity_id + specific gap]
- Uncovered: [spec elements with no test]
- All clear: system behaviour matches spec corpus.
```

Announce in chat: one-paragraph summary of overall status, then paste the full report. Always end with next-step recommendations.

---

## Gotchas

- **L5 ops must declare `run_command` and `port` for Phase 3 auto-start.** If absent, ask before attempting to start.
- **Exact contract failure blocks behavioral reasoning.** You cannot reason about behavior from a malformed response — record `behavioral: SKIPPED — contract failed` and move on.
- **Do not retry failed live probes automatically.** Record failures. Let the human decide whether to re-run with `--scope <id>`.
- **DECLARATIVE atoms have no live probe.** Skip Phase 3 for them entirely — they declare data shapes, not behavior.
- **Behavioral assertions must include rationale.** A bare PASS or FAIL without a sentence explaining the reasoning is not acceptable.
- **Log reading is best-effort.** Unknown log location → `UNVERIFIABLE`, not `NOT FOUND`. These are different findings.
- **`--scope <module_id>` matches all atoms prefixed by `<module_id>.`** Do not require an exact id match for module-level scoping.
- **Report is written even on partial run.** Phases that did not execute are marked `SKIPPED` with a reason. Never omit the report.
- **Idempotency check fires the probe twice.** The second call is against the same `BASE_URL` with the same payload. If the spec does not imply idempotency, skip it.

## forge CLI commands used

| Command | Used for |
|---|---|
| `forge list --kind atom --ids-only --spec-dir <dir>` | Enumerate target atoms |
| `forge context <id> --spec-dir <dir>` | Load full spec + architecture for each atom |
| `forge inspect <id> --spec-dir <dir>` | Metadata probe (kind, module) |

## References

- `references/framework.md` — full mental model (§3 static analysis, §4 test mapping, §5 live probes, §6 report schema)
- `implementation-plan.yaml` — source file mapping, test command, audit matrix paths
- L5 ops spec — `run_command`, `port`, `health_check_path`, `readiness_timeout`, `log_file`
