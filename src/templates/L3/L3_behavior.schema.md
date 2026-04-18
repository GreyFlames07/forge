# L3 — Units of Behavior Schema

**Purpose**: Atoms (executable behavior) and Artifacts (non-executing dependencies). Atoms are the smallest spec unit that produces code.

**Scope**: Per-atom, per-artifact.

**File format**: YAML. Atoms at `L3_atoms/<ATOM_ID>.yaml`. Artifacts at `L3_artifacts/<ARTIFACT_ID>.yaml`.

---

## L3.A — Atom Spec

Every atom has shared fields plus a discriminated `spec` block whose shape is determined by `kind`.

### Top-level structure

```yaml
atom:
  id:              <atom_id>
  kind:            PROCEDURAL | DECLARATIVE | COMPONENT | MODEL
  owner_module:    <module_id>
  description:     <string>

  spec: { ... }

  verification:
    property_assertions: [<expression>, ...]
    example_cases:
      - input:    <value>
        expected: <value | error_code | "success">
    edge_cases: [<string>, ...]

  convention_overrides:
    - field:         <dotted.path>
      value:         <value>
      justification: <string>

  policy_overrides:
    - policy:        <policy_id>
      action:        opt_out
      justification: <string>

  changelog: [...]
```

---

### L3.A.1 — Shared Fields

```yaml
atom:
  id:           <atom_id>
  kind:         PROCEDURAL | DECLARATIVE | COMPONENT | MODEL
  owner_module: <module_id>
  description:  <string>
```

| Field | Description |
|---|---|
| `id` | Unique atom identifier. Must match `naming_ledger.atom_id`. |
| `kind` | Discriminator. One of four values: `PROCEDURAL`, `DECLARATIVE`, `COMPONENT`, `MODEL`. Selects which `spec` sub-schema applies. |
| `owner_module` | Module that owns this atom. Must match a real module that lists this atom in `owned_atoms`. |
| `description` | What value-add logic this atom provides. Should explain what it does and why it exists. |

No `secondary_kind`. Four kinds are sufficiently distinct that dual-kind atoms are not needed. If an atom seems to need two kinds, decompose it.

---

### L3.A.2 — Verification

```yaml
verification:
  property_assertions: [<expression>, ...]
  example_cases:
    - input:    <value>
      expected: <value | error_code | "success">
  edge_cases: [<string>, ...]
```

| Field | Description |
|---|---|
| `property_assertions` | Universal rules that must hold for every execution. Pseudo-formal expressions over input, output, and state. Must meet or exceed L1 `verification.floors.min_property_assertions`. |
| `example_cases` | Concrete input/expected-output pairs for direct testing. Must meet or exceed L1 `verification.floors.min_example_cases`. |
| `edge_cases` | Boundary conditions described in words that test generation must cover. Must meet or exceed L1 `verification.floors.min_edge_cases`. |

MODEL atoms must additionally include a `bounds_verification` sub-section (see MODEL kind below).

---

### L3.A.3 — Convention Overrides

```yaml
convention_overrides:
  - field:         <dotted.path>
    value:         <value>
    justification: <string>
```

Optional. Overrides specific L1 convention fields for this atom only. Each override must target a path listed in L1 `overrides.allowed_fields`. `justification` is required if L1 `overrides.requires_justification` is `true`.

Distinct from `policy_overrides` — this adjusts *L1 conventions* (log levels, retry counts, etc.), not L2 policies.

---

### L3.A.4 — Policy Overrides

```yaml
policy_overrides:
  - policy:        <policy_id>
    action:        opt_out
    justification: <string>
```

Optional. Only present when an atom opts out of a policy applied to its owning module. Legal only when the policy's `opt_out.allowed` is `true`. `justification` required when the policy's `opt_out.requires_justification` is `true`.

---

### L3.A.5 — Changelog

Standard changelog.

---

## L3.A.6 — Discriminated Spec Block

Four shapes. `kind` selects which one applies.

---

### Kind: PROCEDURAL

Executes steps, returns a value. The universal default for functions, handlers, CLI commands, API logic, event processors, pipeline stages, protocol handlers, solvers, and any atom that takes input, does work, and returns output.

```yaml
spec:
  input:  <type_id | inline_fields>
  output:
    success: <type_id | inline_fields>
    errors:  [<error_code>, ...]
  side_effects: [<marker>, ...]
  invariants:
    pre:  [<expression>, ...]
    post: [<expression>, ...]
  logic: [<guarded_step>, ...]
  failure_modes:
    - trigger: <string>
      error:   <error_code>
```

| Field | Description |
|---|---|
| `input` | Input contract. Either a reference to an L0.4 entity type or inline field definitions following the same `{name: {type, nullable, description}}` shape as L0 entities. |
| `output.success` | Shape returned on success. Same format options as input. |
| `output.errors` | Error codes this atom can return. Each must exist in L0.3. Callers use this to know what failures to handle. |
| `side_effects` | Side-effect markers from L0.6. Determines which L1 conventions apply (audit, idempotency). |
| `invariants.pre` | Conditions that must be true on entry. Pseudo-formal rules over input fields and system state. |
| `invariants.post` | Conditions that must be true on exit. Pseudo-formal rules over output and system state. |
| `logic` | Ordered list of guarded steps. See Logic Syntax below. |
| `failure_modes` | Atom-specific failure triggers mapped to error codes. Recovery behavior comes from L1 failure convention based on error category. |

**Logic syntax for guarded steps:**

- `WHEN <condition> THEN <action>` — conditional.
- `WHEN <condition> THEN <action> ELSE <action>` — conditional with alternative.
- `LET <name> = <expression>` — bind a value.
- `LET <name> = CALL <atom_id> WITH <args>` — invoke another atom.
- `CALL <atom_id> WITH <args>` — invoke without binding.
- `RETURN <value | error_code>` — exit the atom.
- `EMIT <event_name> WITH <payload>` — emit an event.
- `SET <state_path> = <value>` — mutate state.
- `TRY: <action> CATCH <condition>: <action>` — error handling.

All conditions and values must reference typed fields. No free prose in the operational part.

**Reference forms inside logic:**

- `const.<CONSTANT_ID>` — references an L0.5 constant. Must resolve.
- `external.<schema_id>.<operation>` — references an L0.7 external service. `schema_id` must resolve; the module must list the schema in its `access_permissions.external_schemas`.
- `<atom_id>` (inside `CALL` or `LET ... = CALL`) — references another atom. Cross-module calls must respect the owning module's `dependency_whitelist`.

---

### Kind: DECLARATIVE

Describes desired state, idempotent. Database schemas, Terraform resources, config files, infrastructure-as-code, CSS definitions.

```yaml
spec:
  target:        <string>
  desired_state: <structure>
  reconciliation:
    strategy:    migration | replace | merge
    on_conflict: fail_and_report | overwrite | manual
  failure_modes:
    - trigger: <string>
      error:   <error_code>
```

| Field | Description |
|---|---|
| `target` | What kind of state is being declared: `database_schema`, `infrastructure`, `style`, `config`, `file`, etc. Categorizes intent for the implementing agent. |
| `desired_state` | The actual declaration. Structure varies by target. For a database schema: table definitions with columns, types, constraints, indexes. For infrastructure: resource declarations. Uses L0.4 types where applicable. |
| `reconciliation.strategy` | How to reach desired state from current state. `migration` generates incremental changes; `replace` tears down and rebuilds; `merge` patches missing parts. |
| `reconciliation.on_conflict` | What to do when desired state conflicts with current state. |
| `failure_modes` | Reconciliation-specific failures (desired state unreachable, constraint conflict, etc.). |

---

### Kind: COMPONENT

Renders UI, holds local state, emits events. Applies to any component-model UI framework (declarative tree of typed props, local state, event emissions). Screens, form widgets, CLI TUI elements all fit.

```yaml
spec:
  props:       <inline_fields>
  local_state: <inline_fields | null>
  composes:    [<atom_id>, ...]
  events_emitted:
    - name:         <string>
      payload_type: <type_id | null>
  render_contract: [<render_rule>, ...]
  invariants:      [<expression>, ...]
```

| Field | Description |
|---|---|
| `props` | Typed properties accepted from parent. Inline field definitions. |
| `local_state` | Internal state the component manages. `null` if stateless. |
| `composes` | Atom IDs this component renders as children. Each must be `kind: COMPONENT`. |
| `events_emitted` | Events this component can emit upward or to the system. Each has a name and optional typed payload. Names are component-local identifiers (single words like `submit`) or fully-qualified system events matching `naming_ledger.event_name`. |
| `render_contract` | Ordered list of render rules defining display and reactions. See Render Rule Syntax below. |
| `invariants` | Rules that must hold about the component's state and rendering. |

**Render rule syntax:**

- `ALWAYS RENDER <atom_id> WITH <prop_bindings>` — unconditional child render.
- `WHEN <condition> THEN RENDER <atom_id> WITH <prop_bindings>` — conditional render.
- `ON <event> DO <action>` — reaction to user/lifecycle events. Actions: `SET local_state.*`, `CALL props.*` (callbacks), `EMIT <event_name>`.

---

### Kind: MODEL

Probabilistic, has acceptable bounds rather than exact outputs. ML classifiers, prediction models, heuristic matchers.

```yaml
spec:
  input_distribution:  <inline_fields>
  output_distribution: <inline_fields>
  acceptable_bounds:
    <metric_name>: <threshold_expression>
  training_contract:
    data_source:           <artifact_id>
    min_samples:           <integer>
    drift_check_frequency: <string>
    retrain_trigger:       <expression>
  fallback:
    when:   <condition>
    invoke: <atom_id>
```

| Field | Description |
|---|---|
| `input_distribution` | Typed fields describing expected input shape and distribution. |
| `output_distribution` | Typed fields the model produces, including confidence/probability fields. |
| `acceptable_bounds` | Named metrics with threshold expressions. The correctness contract for a probabilistic atom. |
| `training_contract.data_source` | Artifact ID of training dataset. Must resolve in L3 artifacts. |
| `training_contract.min_samples` | Minimum training samples for a valid model. |
| `training_contract.drift_check_frequency` | How often to check for data drift. |
| `training_contract.retrain_trigger` | Condition triggering retraining. Pseudo-formal over bound metrics. |
| `fallback.when` | Condition invoking deterministic fallback instead of model. |
| `fallback.invoke` | Atom ID of deterministic fallback. Must be `kind: PROCEDURAL`. (DECLARATIVE atoms describe state, not outputs — they cannot substitute for a model's probabilistic output.) |

**Kind-specific verification requirement:** MODEL atoms must include a `bounds_verification` sub-section in their `verification` block.

---

## L3.B — Artifact Spec

Non-executing dependencies: datasets, model weights, config bundles, prompt templates, localization files, test fixtures.

```yaml
artifact:
  id:           <artifact_id>
  owner_module: <module_id>
  description:  <string>

  format: <string>
  schema: <type_id | inline_fields | null>

  provenance:
    produced_by:      <atom_id | "external" | "manual">
    source_artifacts: [<artifact_id>, ...]
    produced_on:      <YYYY-MM-DD>

  storage:
    location:          <uri>
    access_policy:     read_only | append_only | read_write
    access_allowed_to: [<atom_id | module_id>, ...]

  consumers: [<atom_id>, ...]

  retention_policy: <string>

  changelog: [...]
```

| Field | Description |
|---|---|
| `id` | Unique artifact identifier matching `naming_ledger.artifact_id`. |
| `owner_module` | Module that owns this artifact. |
| `description` | What this artifact is and why it exists. |
| `format` | File/data format: `parquet`, `json`, `yaml`, `csv`, `binary`, `weights`, etc. |
| `schema` | Structural shape. L0.4 type reference, inline fields, or null for opaque blobs. |
| `provenance.produced_by` | What creates this artifact. Atom ID, `"external"`, or `"manual"`. |
| `provenance.source_artifacts` | Upstream artifacts this is derived from. |
| `provenance.produced_on` | Date of last production. |
| `storage.location` | URI: `s3://`, `file://`, `db://`, etc. |
| `storage.access_policy` | `read_only`, `append_only`, or `read_write`. |
| `storage.access_allowed_to` | Atoms or modules permitted to access. |
| `consumers` | Atoms that depend on this artifact. For impact analysis. |
| `retention_policy` | How long to keep. |
| `changelog` | Standard. |

---

## Validation Rules

### Shared atom validation (stage 2)

1. `atom.id` matches `naming_ledger.atom_id`.
2. `atom.owner_module` resolves to a real module that lists this atom in `owned_atoms`.
3. `atom.kind` is one of: `PROCEDURAL`, `DECLARATIVE`, `COMPONENT`, `MODEL`.
4. `verification` meets L1 floor requirements.
5. Every `convention_overrides[].field` matches (after `<category>` placeholder substitution) a path in L1 `overrides.allowed_fields`. For example, `failure.defaults.NET.retries` matches the L1 pattern `failure.defaults.<category>.retries` when `NET` is a key in L0 `error_categories`. `justification` is present when L1 `overrides.requires_justification` is `true`.
6. Every `policy_overrides` entry references a policy applied to the owning module, and opt-out is legal per that policy.
7. Changelog has at least one entry.

### Kind-specific schema validation (stage 3)

8. The `spec` block contains exactly the fields mandatory for the declared `kind`.
9. No fields from other kinds are present.

### Cross-reference validation (stage 4)

10. Every `type_id` referenced in `spec` resolves in L0.4 `types`.
11. Every `error_code` in `output.errors` or `failure_modes` resolves in L0.3 `errors`.
12. Every error code's module prefix matches `atom.owner_module`.
13. Every `atom_id` referenced (in `CALL`, `composes`, `fallback`, etc.) resolves to a real atom.
14. Every side-effect marker in `side_effects` resolves in L0.6 `side_effect_markers`.
15. Every `const.<CONSTANT_ID>` reference in `logic` or `invariants` resolves in L0.5 `constants`.
16. Every `external.<schema_id>.*` reference in `logic` resolves to an L0.7 `external_schemas` entry, AND the `schema_id` is listed in the owning module's `access_permissions.external_schemas`.
17. Every event name in `EMIT` actions and `events_emitted.name` (when not a component-local identifier) matches `naming_ledger.event_name`.
18. COMPONENT atoms' `composes` list contains only COMPONENT atoms.
19. MODEL `fallback.invoke` references a PROCEDURAL atom.
20. MODEL `training_contract.data_source` resolves to a real artifact.
21. Cross-module atom calls respect the calling atom's module's `dependency_whitelist`.

### Kind-specific invariant checks (stage 5)

22. **PROCEDURAL**: every path in `logic` terminates via `RETURN`; every possible return is either the success type or a code from `failure_modes`.
23. **DECLARATIVE**: `desired_state` is internally consistent; `reconciliation` strategy is declared.
24. **COMPONENT**: every field referenced in `render_contract` exists in `props` or `local_state`; every `events_emitted` is triggered by at least one `ON` rule.
25. **MODEL**: `acceptable_bounds` has at least one metric; `fallback.invoke` is PROCEDURAL; `bounds_verification` present in verification.

### Artifact validation

26. `artifact.id` matches `naming_ledger.artifact_id`.
27. `artifact.owner_module` resolves and lists this artifact in `owned_artifacts`.
28. If `schema` references a `type_id`, it resolves in L0.4 `types`.
29. If `provenance.produced_by` is an atom ID, it resolves.
30. Every `source_artifacts` entry resolves.
31. Every `consumers` entry resolves to a real atom.
