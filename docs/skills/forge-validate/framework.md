# forge-validate — Framework Reference

This document is the human-facing mental model for `forge-validate`. The agent reads `SKILL.md`; this file is for contributors, maintainers, and humans who want to understand why the skill works the way it does.

---

## §1 Position in the pipeline

```
forge-implement  →  working system
                        ↓
                 forge-validate    ← you are here
                        ↓
              validation-report.md
```

`forge-validate` runs after `forge-implement` has written code and tests. It assumes:

- Spec corpus exists and is readable via the `forge` CLI.
- `implementation-plan.yaml` exists in the spec dir, mapping entity ids to source files, test commands, and audit matrix locations.
- Source files exist on disk (they may or may not compile/pass tests — that is what Phase 2 determines).
- The system may or may not be running (Phase 3 handles both cases).

`forge-validate` is read-only. It never touches specs or implementation. If it finds gaps, it surfaces them in the report for the human to act on — typically by routing back to `forge-atom` (spec revision), `forge-implement --resume` (re-implementation), or manual fix.

---

## §2 Operating principles

**Three-phase coverage.** A spec corpus makes claims at three levels: structural (does the code have the right shape?), test (does the test suite cover the declared contracts?), and behavioral (does the running system actually behave as specified?). Validating at only one level misses whole classes of defect. All three must run for a complete picture.

**Exact + behavioral duality.** L3 atoms declare explicit output schemas (exact, machine-checkable) and also carry implied logic — idempotency, ordering, invariants, consistency — that is only verifiable by reasoning from the spec in context. The skill applies exact matching where the spec is explicit and LLM reasoning where it is implied. Both are first-class findings.

**Evidence over inference for side effects.** Side effects are the hardest class of behavior to verify. The skill requires log evidence — a matching line in the process output or declared log file — before recording a side effect as `FOUND`. `UNVERIFIABLE` (log location unknown) and `NOT FOUND` (log searched, no match) are distinct findings with different severity.

**Persistence.** `validation-report.md` is a first-class artifact. It is written to the spec dir and persists across sessions. Each run overwrites it. The timestamp in the report header lets you compare successive runs.

**Partial is acceptable.** A run that completes Phase 1 and Phase 2 but fails to start the system for Phase 3 is still useful. The report captures exactly what ran and what was skipped. Never abort early and leave the report unwritten.

---

## §3 Phase 1 — Static analysis mechanics

Static analysis reads source files and reasons about whether they satisfy the L3 spec contract. It does not execute code.

### What it checks

| Check | How |
|---|---|
| Input handling | Scan for field validation / parsing code matching each L3 `input` field |
| Output shape | Scan all return paths for the declared `output` fields |
| Failure mode coverage | Scan for error-return paths matching each `failure_modes[*].error_code` |
| Side effect backing | Scan for call patterns (DB write, event emit, HTTP call, log) matching each `side_effects` marker |

### Why static analysis runs before tests

Tests may themselves be wrong or incomplete. Static analysis gives an independent read: "does this code, on its face, implement the contract?" A passing test suite against a mis-implementing function is possible (especially with overly permissive assertions). Static analysis catches structural gaps tests miss.

### Severity logic

- `FAIL` — a declared spec element has no backing code at all. The gap is unambiguous.
- `WARN` — the element exists but something is inconsistent (wrong HTTP status, extra fields, partial handling). The behavior may or may not be correct — human judgment needed.
- `PASS` — code structure matches spec declaration.

---

## §4 Phase 2 — Test suite mapping mechanics

Phase 2 runs the real test suite and maps results back to the spec corpus.

### Audit matrix

`forge-test-writer` writes an audit matrix alongside each test file. Each row maps a test name to the spec element it derives from (`entity_id`, `spec_element` path, `level`). forge-validate loads these matrices to make the mapping.

If an audit matrix is missing for a unit, that unit's tests are counted in the total pass/fail but cannot be mapped to spec elements — all those spec elements are marked `uncovered`.

### Uncovered finding

A spec element with no audit matrix row means: there is no declared test for it. This is a coverage gap — not necessarily a bug, but a risk. The report surfaces these so the human can decide whether to add coverage or accept the gap.

### Coverage numbers

If the test runner emits coverage data, forge-validate records line and branch coverage at the project level. It does not enforce a threshold — that is the CI's job. Coverage is reported as context, not a pass/fail gate.

---

## §5 Phase 3 — Live interaction mechanics

Phase 3 is the most complex phase. It requires a running system and fires real HTTP/RPC calls against it.

### System startup

forge-validate reads the L5 ops spec for `run_command`, `port`, `health_check_path`, and `readiness_timeout`. If the system is already up (health endpoint returns 200), forge-validate connects to it without starting anything. This means you can run forge-validate against a staging environment by passing `--url` without needing L5 ops to declare a local run command.

The startup flow is:

```
probe health endpoint
  → 200: already running → use it
  → fail: read L5 ops run_command
    → found: start subprocess, poll until ready or timeout
      → ready: proceed
      → timeout: mark Phase 3 SKIPPED, write report, exit
    → not found: ask user
```

### Probe construction

Probes are constructed from the L3 `input` schema:

1. Use any `example` values declared on input fields.
2. For fields without examples: infer minimal valid values from declared types and constraints (e.g. `string` → `"test"`, `integer` → `1`, `email` → `"test@example.com"`).
3. For failure mode probes: use the `trigger` field to determine which constraint to violate (e.g. `trigger: amount <= 0` → set `amount: -1`).

### Route derivation

forge-validate derives the HTTP method and path for each atom from:

1. L2 module routing conventions declared in the architecture section of `implementation-plan.yaml`.
2. Side effect patterns on the atom (e.g. a `DB_WRITE` side effect on a `COMMAND` atom implies a POST/PUT).
3. If still ambiguous: ask the user once with a table of all ambiguous atoms (not once per atom — batch the question).

### Exact vs behavioral assertion

**Exact:** field-by-field comparison of the response body against the L3 `output` schema. This is deterministic. A required field absent is always a FAIL.

**Behavioral:** LLM reasoning from the full spec context. The agent loads `forge context <id>` and reasons about what the spec implies beyond its explicit output schema. This is not deterministic — it requires judgment. The key invariants to probe:

| Invariant | How to probe |
|---|---|
| Idempotency | Re-fire the same call; expect identical response |
| State machine | Fire transitions in declared order; fire out-of-order (expect rejection) |
| Business invariants | Probe boundary conditions implied by spec description (e.g. balance floor) |
| Consistency | Create then immediately read; verify entity exists with correct shape |

The behavioral PASS/FAIL rationale must be written as a full sentence. *"PASS — re-firing the charge call with the same idempotency key returned the same charge_id and status, consistent with the idempotency guarantee implied by the spec."*

### Side effect verification

After each probe, forge-validate reads the system logs and searches for evidence of each declared side effect. The log is read from:

1. Process stdout/stderr (for processes started by forge-validate).
2. `log_file` path declared in the L5 ops spec (for external processes).
3. If neither: `UNVERIFIABLE`.

Search strategy: case-insensitive substring match on the side effect marker name, event name, or any log pattern declared on the marker. If found: record the matching log line. If not found after reading all logs: `NOT FOUND`.

`NOT FOUND` is a FAIL. `UNVERIFIABLE` is a WARN — the side effect may have fired but forge-validate cannot confirm it.

---

## §6 Report schema

The report is a Markdown document written to `<spec-dir>/validation-report.md`. Key fields:

| Section | Content |
|---|---|
| Summary table | Phase × (Status, Pass, Warn, Fail) counts |
| Overall status | PASS (no FAILs anywhere) / FAIL (any FAIL) / PARTIAL (a phase was SKIPPED) |
| Phase 1 detail | Per-atom findings with gap descriptions |
| Phase 2 detail | Failing test → spec element mapping; uncovered spec elements |
| Phase 3 detail | Per-atom probe results: happy path, failure modes, side effects |
| Next steps | Actionable routing: which skill to invoke for which gap |

**Overall PASS** requires: no FAIL findings in any completed phase. WARNs do not block PASS.

**Overall PARTIAL** means one or more phases were SKIPPED (startup failure, `--skip-*` flag). A PARTIAL report is still useful — it shows what was validated.

---

## §7 Routing from findings

| Finding | Recommended action |
|---|---|
| `source_missing` | Run `/forge-implement --resume --restart <id>` |
| Static `FAIL` — missing failure mode | Inspect implementation; may need `/forge-atom <id>` to clarify spec |
| Test `FAIL` mapped to spec | Fix implementation or spec; re-run `/forge-implement --resume` |
| Test `uncovered` | Add test via `/forge-test-writer` or accept gap |
| Live contract `FAIL` | Fix implementation; re-validate with `--scope <id>` |
| Live behavioral `FAIL` | Often a spec ambiguity — run `/forge-atom <id>` to clarify |
| Side effect `NOT FOUND` | Inspect implementation and logging; may be missing a log call |
| Side effect `UNVERIFIABLE` | Declare `log_file` in L5 ops spec and re-run |

---

## §8 What forge-validate does NOT do

- **Does not modify specs.** All findings are in the report only.
- **Does not modify implementation.** Gaps are surfaced, not fixed.
- **Does not retry failed live probes.** One probe per atom per run. Re-run with `--scope` to re-probe a specific atom after a fix.
- **Does not enforce coverage thresholds.** It reports coverage numbers; enforcement is CI's responsibility.
- **Does not run performance or load tests.** Latency is recorded per probe but not asserted against. That is a separate concern.
- **Does not validate L0–L2 spec consistency.** That is `forge-audit`'s domain. forge-validate assumes the spec corpus is already audited.

---

## §9 Artifact schema

`validation-report.md` is a Markdown file. There is no separate YAML artifact — the report is human-readable only.

Future versions may emit a machine-readable `validation-results.yaml` alongside the Markdown. For now, parsers should scrape the summary table.

---

## §10 Running forge-validate in CI

forge-validate can be invoked in CI for post-deploy smoke validation. Recommended setup:

1. Pass `--url <deployed_base_url>` to skip local startup.
2. Pass `--skip-static` (static analysis is more useful during development than post-deploy).
3. Use `--scope <critical_module_id>` to limit scope to the most critical atoms and keep CI time manageable.
4. Exit code: 0 on PASS or PARTIAL; 1 on any FAIL finding.

CI invocation example:

```bash
forge-validate --url https://staging.example.com --skip-static --scope PAY
```

The skill writes `validation-report.md` to the spec dir. CI can archive this as a build artifact.
