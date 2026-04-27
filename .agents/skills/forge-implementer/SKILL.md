---
name: forge-implementer
description: >
  Use this skill when the forge-implement orchestrator dispatches an
  implementation task for a Forge spec entity (atom, flow, or journey).
  This skill is not typically invoked by a human directly — it is a
  subagent skill. Takes an entity id + kind + target code file paths +
  the architecture block from the orchestrator. Loads the spec via
  forge context, generates implementation code respecting the
  architecture's decisions (language, frameworks, error handling
  pattern, DI strategy, naming policy). Blind to tests — never reads
  test files. Minimality: produces only the smallest set of code
  necessary to satisfy the spec.
---

# forge-implementer

Subagent dispatched by `forge-implement` to generate implementation code for one Forge entity (atom / flow / journey). You read the spec via `forge context`, generate code, write file(s), and exit.

## Inputs (from orchestrator)

- `entity_id` — atom id, flow id, or journey id
- `kind` — the entity's declared `kind` (PROCEDURAL / DECLARATIVE / COMPONENT / MODEL for atoms; flow / journey for those)
- `target_source_file` — absolute path(s) where implementation is written
- `architecture` — block from `supporting-docs/implementation-plan.yaml` (language, frameworks, error handling, DI, naming, schema/iac tool, etc.)
- `retry_feedback` — optional, present on retries only; contains sanitized failure output + spec-linked hints per forge-implement's D4

Load `references/framework.md` when you need to make judgment calls about minimality, architecture conflicts, or the isolation principle.

## Non-negotiables

1. **Never read test files.** You will be told nothing about tests. Even if test files exist on disk, never open them.
2. **Implement the spec, not a guess.** Every function, every error path, every side effect traces back to a declared item in the spec.
3. **Minimality.** Produce only the smallest set of code necessary to satisfy the spec. No extra abstractions, layers, helpers, or boilerplate unless strictly required for correctness or explicitly declared in the architecture (e.g., "use DI factory pattern" — include only what the pattern requires).
4. **Respect the architecture block.** Language version, error handling pattern, DI strategy, naming policy, schema/iac tool, UI framework — all dictated by the architecture block the orchestrator passed. Do not override.
5. **Stop after write.** Do not also write tests. Do not modify the spec. Do not touch other files outside the target paths.

## Step 1 — Load context

```bash
forge context <entity_id> --spec-dir <spec-dir>
```

Parse the bundle:
- For atom: `spec` (input, output, side_effects, invariants, logic, failure_modes), L0 slice (types, errors, constants the atom uses), L2 module (tech_stack, access_permissions, policies applied).
- For flow: sequence (the steps to orchestrate), transaction_boundary, trigger, state_transitions.
- For journey: handlers, transitions, entry_point, exit_states.

Read the architecture block. This tells you: language, frameworks, error handling, DI strategy, naming, etc.

## Step 2 — Generate code by entity kind

### Atom: PROCEDURAL

Translate the `logic` DSL into idiomatic code for the architecture's language. Every `WHEN / LET / CALL / RETURN / EMIT / SET / TRY` step maps to real code:

- `WHEN <cond> THEN RETURN <error>` → a guard clause returning / throwing the declared error per the error handling pattern.
- `LET <var> = CALL <atom>` → an import of the called atom (per DI strategy) + an invocation with the declared args.
- `LET <var> = CALL external.<schema>.<op>` → a call to the external service per module's `access_permissions.external_schemas` binding (the tool / client).
- `TRY: <action> CATCH <cond>: <action>` → try/catch block (in exception-based error handling) OR a Result / Either chain (in that pattern).
- `EMIT <event> WITH <payload>` → a call to the project's event bus / emitter per module/architecture.
- `SET <state>` → a state mutation (e.g., DB write via the schema tool).
- `RETURN <value | error>` → return statement idiomatic to the language.

Imports: reference types from the shared scaffolding the orchestrator generated (per architecture). Reference L0 constants from the generated constants module. Reference sibling atoms via imports following architecture's DI strategy.

Declare function signature matching the spec's `input` and `output.success` types. Declare error returns matching `output.errors`.

Implement every `invariants.pre` as a guard at the top of the function (per error handling pattern). `invariants.post` is a property of the logic, not code — don't generate runtime assertions for post conditions unless the architecture explicitly requires them.

Implement every `failure_modes.trigger → error` mapping as a branch in the logic that returns the declared error.

### Atom: DECLARATIVE

Produce the declared desired state in the architecture's `schema_tool` (for database_schema target) or `iac_tool` (for infrastructure target) or language-idiomatic format (for config / style / file targets). Examples:

- `target: database_schema`, schema_tool: prisma → write a `.prisma` schema block declaring the model per `desired_state`.
- `target: database_schema`, schema_tool: raw-sql → write a SQL migration file with CREATE TABLE / ALTER TABLE statements.
- `target: infrastructure`, iac_tool: terraform → write a `.tf` file with resources.
- `target: config` → write a language-idiomatic config file (YAML / JSON / TOML).

Respect `reconciliation.strategy` and `reconciliation.on_conflict` declarations — these often map to migration strategy flags or IaC state policies.

### Atom: COMPONENT

Produce a UI component per the architecture's UI framework. Map spec fields:
- `props` → component props / parameters
- `local_state` → local state declarations (`useState`, `ref`, `reactive`, etc.)
- `composes` → child components imported and rendered
- `events_emitted` → callback props the component invokes
- `render_contract` → rendering tree + event handlers
- `invariants` → assertions only if the architecture specifies dev-mode assertions; otherwise skip

Respect the styling approach from architecture (Tailwind classes vs CSS module imports vs styled-components literals).

### Atom: MODEL

Produce the stub-plus-loader-scaffold per E6:
- Try to load a trained model (TODO-commented loader).
- If model is loaded and confidence ≥ the declared `acceptable_bounds` threshold, use the model's prediction.
- Otherwise, delegate to the declared `fallback.invoke` atom.
- Import and expose `acceptable_bounds` as constants.
- `training_contract` details stay as a block comment at the top of the file (human will wire actual training separately).

### Flow

Produce the orchestration code composing the atoms in `sequence`. Each step maps to a call to the declared atom. Implement the `transaction_boundary`:
- `acid` → wrap the whole sequence in a DB transaction per schema_tool's API.
- `saga` → each step's `compensation` is a reverse-order rollback action on failure.
- `none` → just sequential calls with error handling per `on_error` map.

Implement `on_error` actions: `HALT`, `HALT_AND_EMIT <event>`, `RETRY(max=<n>)`, `GOTO step=<label>`, `CONTINUE`, `COMPENSATE_AND_HALT`.

`state_transitions.emit` → emit events at the declared outcome points.

### Journey

Produce the user-facing flow code per the `surface`:
- `web_ui` / `mobile_ui` → a router + state machine + entry component chain using the project's UI framework.
- `api` / `cli` → a handler / command per entry_point.
- `conversation` / `email_sequence` → a sequencer per the transition rules.

Each state's `handlers.atom` is invoked via the architecture's DI strategy. Transitions map to state-machine transitions. Exit states terminate the journey.

## Step 3 — Apply the formatter

After writing all target files, apply the architecture's formatter to each file (this is what the orchestrator will do anyway; doing it here keeps output clean). For example, for TypeScript: `prettier --write <target>`. For Python: `black <target>`. For Go: `gofmt -w <target>`. If the architecture specifies a custom formatter config path, pass it.

## Step 4 — Report to orchestrator

Return a summary:
```
source_files: [<paths>]
lines_written: <N>
imports_used:  [<module paths>]
architecture_conflict: false   # or true, with reason, if J3 conflict encountered
```

If the spec is genuinely incompatible with the architecture (e.g., spec requires async but architecture says sync-only), set `architecture_conflict: true` with a concrete reason, and write nothing to target files. The orchestrator will cancel dependents per J3.

## Retry behavior

If `retry_feedback` is present in the orchestrator's input, it contains sanitized failure output + spec-linked hints. Do NOT read test files. Instead, use the spec-linked hints to adjust implementation:
- *"Test `test_unit_failure_mode_PAY_VAL_001` failed. This test derives from failure_modes trigger 'amount <= 0'. Your implementation did not return PAY.VAL.001 for this input."* → review the logic branch for the `WHEN amount <= 0` case; ensure it returns the declared error.

Do not make implementation decisions based on guessing test expectations. The feedback is spec-linked; treat it as a pointer back to the spec element to review.

## Gotchas

- **Minimality** is a hard constraint. If the architecture says "use direct imports" and the spec has one CALL, import that one dependency. Don't introduce a container / registry / service locator.
- **No speculative error handling.** If `output.errors` declares 3 codes, write 3 branches — no "for safety, add a generic catch-all." The spec is the contract; staying inside it is the discipline.
- **No logging unless the architecture or spec declares it.** L1 conventions declare observability templates (on_entry, on_success, on_failure). Implement exactly those — nothing more.
- **Never read the test file.** Not even to "check what the test expects." The failure feedback goes through spec-linked hints; that's sufficient.
- **Never modify other atoms' implementations.** Even if you think sibling atoms have bugs. Each subagent owns one entity.
- **Never write to the spec directory.** Specs are frozen.
- **If architecture doesn't specify a decision the spec requires** (e.g., spec needs async but architecture is silent on async pattern): set `architecture_conflict: true` with a clear reason. Human fixes architecture; skill is re-invoked.

## forge CLI commands used

| Command | Used for |
|---|---|
| `forge context <entity_id>` | Step 1 context load |
| `forge inspect <called_atom>` | Get signatures of called atoms if architecture's DI strategy needs them pre-resolved |
