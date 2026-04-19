---
name: forge-implement
description: >
  Use this skill when the user wants to translate a completed, audited
  Forge spec corpus into working implementation — code files, tests, and
  optionally git commits. Activates on phrases like "implement the
  project", "build the code", "let's implement", "run forge-implement",
  or after forge-audit completes cleanly with no open blocking findings.
  Recommends a `forge-armour` pass before implementation when the project
  has meaningful security exposure, but does not require it.
  Dispatches the forge-test-writer and forge-implementer skills via
  Task subagents (subagent_type: general-purpose; skill name invoked
  in the prompt) in parallel per the dependency graph, enforcing strict
  test-before-implementation isolation. Tests cover unit, integration,
  and system levels. Does NOT modify specs — specs are frozen at run
  start. Does NOT make implementation decisions — those live in the
  architecture section of the generated plan (human-confirmed) or in
  the specs themselves.
---

# forge-implement

Orchestrate implementation of a Forge spec corpus. You generate a plan + architecture, gate on audit state, spawn parallel subagents in dep-graph order (test-writer first, then implementer, each in isolated sessions), retry on failure with spec-linked feedback, and hand over. You never write code yourself; you dispatch.

Full mental model in `references/framework.md` (~400 lines). Load on demand:
- `§4` for plan + architecture generation mechanics
- `§7` for the per-unit pipeline (test → red → impl → green → build → format)
- `§10` for retry / failure / resumability details
- `§12` for artifact schemas

Otherwise this file is self-sufficient for routine operation.

## Non-negotiables

1. **Orchestrator is a pure dispatcher.** Never make implementation decisions. Never inline spec content in subagent prompts. Subagents call `forge context` to load their own state.
2. **Specs are frozen during a run.** Never edit spec files. Changes require re-audit + re-invocation.
3. **Test-before-implementation isolation.** Test-writer subagent completes in a fresh session; then implementation subagent runs in a separate fresh session, blind to tests.
4. **Dep graph drives order.** Units run topologically; independents run concurrently up to `--parallelism N` (default 4).
5. **Spec-linked retry feedback only.** Implementation retries receive sanitized failure output with spec references — never test assertion diffs.
6. **Partial completion is fine.** Succeeded units stay; failed units stash attempts; blocked units wait. Resume with `--resume`.
7. **Minimality.** Subagents produce the smallest code satisfying the spec — no speculative abstractions.

Full rationale: `references/framework.md §2`.

## Workflow

### Step 1 — Load or generate plan + architecture

**Invocation flags:**
- `/forge-implement` — full run
- `/forge-implement --resume` — resume from progress.yaml
- `/forge-implement --parallelism <N>` — override subagent cap
- `/forge-implement --skip-audit-check` — skip audit recency gate
- `/forge-implement --force` — proceed despite open blocking findings
- `/forge-implement --skip <entity_id>` / `--manual <entity_id>` / `--restart <entity_id>` / `--retry-override <entity_id>=<N>` — resume adjustments

**Check for existing plan at `<spec-dir>/implementation-plan.yaml`:**
- If present: detect drift — for each unit, compare spec mtime to `plan.generated_at`. Summarize: *"Plan was generated `<date>`. Since then: X new, Y modified, Z deleted. Regenerate plan, or continue with existing?"*
- If human chooses continue: proceed to step 2 with existing plan.
- If regenerate or absent: generate fresh.

**Plan generation:**
1. Enumerate entities: `forge list --kind atom --ids-only`, same for `flow`, `journey`, `artifact`.
2. For each entity: compute kind, target_files (from architecture naming policy), depends_on (from spec — atoms CALLed, DECLARATIVE atoms declaring referenced datastores, artifacts referenced via `READS_ARTIFACT`, sequence/compensation atoms for flows, handler/invoke atoms for journeys).
3. Topologically sort; break ties by module cohesion.
4. Emit `units` list.

**Architecture generation:**
1. **Inferred (silent):** default_source_root, source_root_overrides (from `tech_stack.source_root` per module), atom_naming_policy (per-language idioms), test_frameworks (from `tech_stack.frameworks` or language defaults), schema_tools (from `tech_stack.schema_tool` or defaults), iac_tools (same), error_handling (language idioms), dependency_injection (default direct_imports unless DI framework detected), async_patterns.
2. **Elicited (UI consultation — only if any COMPONENT atoms exist):** ask the human:
   - *"UI framework — inferred as `<X>` from `tech_stack.frameworks`. Confirm, or different?"*
   - *"Styling approach? (Tailwind / CSS modules / styled-components / vanilla / other)"*
   - *"Design system? (none / shadcn / Material / custom — describe)"*
   - *"Responsive strategy? (mobile-first / desktop-first / fluid)"*
   - *"Accessibility target? (WCAG 2.1 AA / not specified)"*
   - *"Theming? (light / dark / light-and-dark / multi-theme)"*
   Record answers in `architecture.ui_*` fields.

**Write plan to disk.** Then pause:

> *"Plan generated: `<N>` units in `<M>` modules. Architecture assembled.*
> *File: `<spec-dir>/implementation-plan.yaml`*
> *Edit now if desired (reorder, modify architecture, adjust target files). Confirm to proceed."*

Wait for confirmation.

### Step 2 — Audit gate

1. Check `<spec-dir>/audit-history.md` exists. If not: *"No audit history. Run `/forge-audit` first."* (Unless `--skip-audit-check`.)
2. Compare most-recent audit timestamp to all spec file mtimes. If any spec is newer: *"Specs changed since last audit. Run `/forge-audit` (or use `--skip-audit-check`)."*
3. Parse audit history for `status: open` findings at severity `blocking`. If any: *"`<K>` blocking findings open: `<list>`. Confirm proceed [y/N] or use `--force`."*
4. If `armour-history.md` exists: summarize any open `blocking` armour findings and require `--force` or explicit confirmation to continue.
5. If `armour-history.md` does not exist: recommend, but do not require, `/forge-armour` when the spec corpus contains sensitive data, external interfaces, authn/authz surfaces, multi-tenant behavior, or high-risk operations.
6. Clean → proceed silently.

### Step 3 — Generate shared scaffolding

Write to disk (not spawned to subagents — direct write from orchestrator):

1. **Types.** For each language in the architecture, generate `src/generated/types.<ext>` materializing every L0 type as a language-native type (TS `interface` / Python `dataclass` / Go `struct` / etc.).
2. **Constants.** Generate `src/generated/constants.<ext>` exporting every L0 constant.
3. **Fixtures.** For each module with COMPONENT or PROCEDURAL atoms that persist entities, generate `tests/fixtures/<mod>.fixtures.<ext>` with factory functions per entity type.

Use architecture's `source_root` and naming conventions. Regenerate on every run — these files are pure spec derivations.

### Step 4 — Execute the plan

Main loop:

```
while any unit has status in {pending, in_flight}:
    ready = [u for u in units if u.status == pending
                                 and all(dep.status == done for dep in u.depends_on)]
    available_slots = parallelism - count(in_flight)
    for u in ready[:available_slots]:
        spawn_pipeline(u)
    wait_any_complete()
    process_completion()
    checkpoint progress.yaml
```

**Per-unit pipeline (spawn_pipeline):**

For each unit, spawn subagents sequentially (test-writer first, then implementer). Maintain in-memory state; checkpoint after each subagent completes.

**Stage 1 — Test-writer:**
- Spawn a Task subagent to execute the `forge-test-writer` skill. **`forge-test-writer` is a skill, not a Task `subagent_type`** — invoke the Task tool with `subagent_type: "general-purpose"` and in the prompt instruct the agent to follow the `forge-test-writer` skill directive (the spawned agent will load it from its skill registry via description-matching).
- The prompt MUST be self-contained (Task subagents inherit no shell state — no `$FORGE_SPEC_DIR`, no CWD assumptions):
  - Absolute `spec_dir` path (pass via `--spec-dir` in every `forge` call, or `export FORGE_SPEC_DIR=<path>` at the top of the prompt).
  - `entity_id`, `level` (unit for atoms; integration for flows; system for journeys), absolute `target_test_file`, absolute `target_audit_file`, `architecture` (block from plan).
  - Explicit write-files instruction: *"Write the test file to `<target_test_file>` and the audit matrix to `<target_audit_file>`."*
- Wait for completion. Subagent returns: `test_file`, `audit_file`, `tests_count`, `framework`.

**Stage 2 — Red phase (D3):**
- Run the test command for the generated test file against an empty/missing implementation.
- Every test should fail (or error because implementation doesn't exist).
- If any test passes trivially: re-spawn test-writer with feedback: *"Test `<name>` passed against an empty stub. Re-generate: the test must assert behavior, not be trivially true."*
- Max 2 test-writer retries. On exhaustion: mark unit `failed` with reason "test-writer produced trivial tests"; block dependents; continue with rest.

**Stage 3 — Implementation-writer:**
- Spawn a Task subagent with `subagent_type: "general-purpose"`; the prompt instructs it to follow the `forge-implementer` skill. Same dispatch semantics as Stage 1 — self-contained prompt, no inherited shell state.
- Inputs in the prompt:
  - Absolute `spec_dir` path.
  - `entity_id`, `kind` (atom kind / flow / journey), absolute `target_source_file`, `architecture`.
  - On retry, include `retry_feedback` (sanitized; see stage 4).
  - Explicit write-files instruction.
- Subagent's prompt does not mention tests. It never reads test files.
- Wait for completion. Subagent returns: `source_files`, `lines_written`, `architecture_conflict` flag.

**Stage 4 — Green phase + retry:**
- If `architecture_conflict: true`: mark unit `failed` with the subagent's reason; cancel all dependents (mark `blocked`); continue with unrelated branches. Do NOT retry.
- Else run the test command against the just-written implementation.
- If all pass: proceed to stage 5.
- If any fail:
  - Capture test output; sanitize by stripping assertion-diff expected-values.
  - For each failing test, map its name (via test-writer's naming policy) back to the spec element it derives from. Build spec-linked hints:
    - *"Test `test_unit_failure_mode_PAY_VAL_001` failed. This test derives from `failure_modes[0]` with trigger `amount <= 0`. Your implementation did not return PAY.VAL.001 for this input."*
  - Re-spawn implementer with `retry_feedback` = sanitized output + hints.
  - Max 2 implementer retries.
  - On exhaustion: mark unit `failed`; stash all attempts per G4 in `implementation/attempts/<entity>/attempt-<N>/`; block dependents; continue.

**Stage 5 — Build check (F2, typed languages only):**
- If language is typed (TypeScript / Go / Rust / Java / Scala / etc.): run compile check on just-written files (`tsc --noEmit <file>`, `go vet ./path`, etc.).
- On failure: treat as test failure — re-spawn implementer with build error as spec-linked feedback.

**Stage 6 — Structural sanity check (F5):**
- Verify: every type in `input`/`output` is imported; every error in `output.errors` is returnable from the code; every side-effect marker has a backing code pattern.
- On any issue: record as low-severity warning in progress.yaml, do NOT fail the unit.

**Stage 7 — Format (F3):**
- Run architecture's formatter on just-written files (prettier / black / gofmt / rustfmt).
- Use repo's config if present; skill's default otherwise.
- No linting.

**Stage 8 — Mark done, checkpoint:**
- Mark unit `status: done`, record `completed_at`, test count, coverage numbers.
- Discard stashed intermediate attempts (keep only on final failure per G4).
- Write progress.yaml.

### Step 5 — Final rollups (F1 rollups, F2 rollup)

After main loop ends:

1. **Full-project test suite.** Run `<test_command>` against the entire project (no `<file>` filter). Capture pass/fail. Record in progress.yaml's `rollup` section.
2. **Full-project build.** For typed languages: run full project build (`tsc --noEmit`, `go build ./...`, `cargo check`). Capture.
3. **Coverage report.** Run the coverage tool if available (`vitest --coverage`, `pytest --cov`, `go test -cover ./...`). Record numbers.

### Step 6 — Handover (H3)

Announce:

```
forge-implement complete.
Scope:           project-wide
Units done:      <N>
Units failed:    <M>
Units blocked:   <K>

Full project test suite: <pass|fail — <X passed, Y failed>>
Full project build:      <pass|fail>
Coverage: line <X>%, branch <Y>%

<if failed units: list them with stash paths>
<if blocking specs issues: routing to forge-audit / forge-atom>

Commit these as per-atom commits? [y/N]
```

If yes:
- For each successful unit, run:
  ```bash
  git add <target_files> && git commit -m "feat(<mod>): implement <entity_id>"
  ```
- Report commits made.

If no: leave files uncommitted.

**Next-step recommendations:**
- Failed units: *"Inspect `implementation/attempts/<id>/`. Options: (a) `/forge-audit --scope <id>` for spec review, (b) `/forge-atom <id>` to revise spec, (c) `/forge-implement --resume --retry-override <id>=5` to try more retries."*
- Clean run: *"Implementation complete. Run your test suite, CI, or deploy pipeline as appropriate."*

## Retry policy summary

| Stage | Max retries | Feedback |
|---|---|---|
| Test-writer (red phase fails) | 2 | Trivially-passing test names; no test content |
| Implementer (green phase fails) | 2 | Sanitized test output + spec-linked hints |
| Implementer (architecture_conflict) | 0 | No retry; cancel + block dependents; human fixes architecture |

Overridable per-unit via `--retry-override <entity_id>=<N>`.

## Resume protocol (G3)

On `/forge-implement` invocation when `progress.yaml` exists:

1. Read progress.yaml. Summarize: *"Last run: N done, M failed, K pending, J in_flight, L blocked. Last activity: `<timestamp>`."*
2. Validate stashed state:
   - Every `status: done` unit's target files still exist on disk?
   - Any spec file modified since `progress_updated_at`?
3. Present:
   - Clean: *"Resume, restart, or review state? [r/s/v]"*
   - Drift: *"`<N>` specs modified since last run: `<list>`. Options: (a) resume anyway; (b) regenerate plan; (c) show diff."*
4. On resume: pick up the main loop from where it left off. In-flight units are re-spawned fresh (Task tool's prior subagent session is lost).

## Gotchas

- **Subagent isolation is structural.** Task tool spawns fresh sessions — subagent contexts cannot see each other. Do not try to pass large spec content in subagent prompts; they run `forge context` themselves.
- **Skills ≠ Task subagent_types.** `forge-test-writer` and `forge-implementer` are skills, not Task `subagent_type` values. Always spawn with `subagent_type: "general-purpose"` and tell the agent *in the prompt* to follow the named skill. Calling `Task(subagent_type="forge-test-writer")` fails with "agent type not found".
- **Subagents inherit no env.** `$FORGE_SPEC_DIR`, CWD, and shell aliases don't cross the Task boundary. Every subagent prompt must include the absolute `spec_dir` path and pass it explicitly (`--spec-dir <path>`) to every `forge` invocation, or set `FORGE_SPEC_DIR=<path>` inline before each call.
- **Never tell the implementer tests exist.** Its prompt mentions only the target source file + spec id + architecture + (on retry) spec-linked hints. No test file paths, no test names, no coverage reports.
- **Test-writer's audit file must have a row per spec element.** Verify the audit file before accepting the test-writer's output. If any spec element is missing from the audit matrix, re-spawn the test-writer with that gap called out.
- **Architecture-conflict is final for the unit.** No retries. The human has to edit the architecture section of the plan and resume. The whole point of J3 is this short-circuits garbage-in-garbage-out loops.
- **Stashed attempts are the debugging artifact.** When a unit fails after exhausted retries, write every attempt's (source, test output, retry feedback) to `implementation/attempts/<id>/attempt-<N>/` so the human can trace what happened.
- **Don't parallelize the two phases within a unit.** Test-writer must complete and red-phase must verify before implementer starts. Parallelizing risks the implementer running before tests are written, getting unclear signal.
- **Partial runs are the norm on big projects.** Expect 10-20% of units to fail on first run of a new project — the spec surface surprises come out. Re-audit + re-resume + iterate.
- **Specs changed mid-run = the whole run is tainted.** Cancel immediately. Re-audit. Re-run.

## forge CLI commands used

| Command | Used for |
|---|---|
| `forge list --kind <kind> --ids-only --spec-dir <dir>` | Plan generation — enumerate entities |
| `forge inspect <id> --spec-dir <dir>` | Plan generation — fetch entity metadata |
| `forge context <id> --spec-dir <dir>` | Not used by orchestrator directly; subagents call it |

## References

- `references/framework.md` — full mental model. Sections:
  - §2 operating principles
  - §3 pipeline overview
  - §4 plan + architecture generation
  - §5 audit gate
  - §6 shared scaffolding generation
  - §7 execution (per-unit pipeline)
  - §8 final rollups
  - §9 handover
  - §10 failure, retry, resumability
  - §11 what forge-implement does NOT do
  - §12 artifact schemas
- `assets/implementation-plan.template.yaml` — canonical plan structure
- `assets/progress.template.yaml` — canonical progress structure
- Subagent skills: `forge-test-writer` and `forge-implementer` (installed alongside)
