# L1 Authoring Guide

L1 Conventions are the project-wide defaults that let atoms focus on value-add logic. Every field here saves verbosity in every atom downstream.

**Core principle**: L1 declares rules over *universal framework vocabulary* — error categories from L0, side-effect markers from L0, log levels. It does not enumerate atom kinds or interface kinds. Kind-specific rules live in the layers where those kinds are defined.

**What L1 is not**: L1 is not where platform/runtime decisions live. Deployment strategy, rate limiting, and event delivery semantics belong in **L5 Operations**. L1 stays focused on atom-level frame logic.

---

## Section 1: observability

### Purpose

Atoms log and trace. If every atom restates logging format, you maintain N copies of the same template. Declare it once here.

### Why metrics are not here

The runtime (OpenTelemetry, Prometheus, etc.) emits invocation count, duration, and error counters automatically at the function-call boundary. Speccing them here is bloat. Atoms that need custom metrics beyond the runtime baseline declare them in their own L3 spec.

### Fields

**`logging.default_level`**
- **What it is**: Log level for non-failure logging (`on_entry` and `on_success` templates).
- **Purpose**: Separates the level decision from the template. Entry and success logs are not errors — they get a single shared level.
- **Typical value**: `INFO`.

**`logging.on_entry`**
- **What it is**: Template string logged at the start of every atom execution.
- **Purpose**: Uniform entry logging. Change the format once; every atom's logs change.
- **Template variables**: `{atom_id}`, `{owner_module}`, `{input_summary}`, `{actor}`, `{trace_id}`.
- **Typical value**: `"{atom_id} started | actor={actor} trace={trace_id}"`
- **Note**: Use `{input_summary}`, never raw input. The runtime redacts sensitive fields based on type metadata from L0.

**`logging.on_success`**
- **What it is**: Template logged on successful return.
- **Template variables**: `{atom_id}`, `{duration_ms}`, `{output_summary}`.
- **Typical value**: `"{atom_id} completed | duration_ms={duration_ms}"`.

**`logging.on_failure`**
- **What it is**: Template logged on error return.
- **Template variables**: `{atom_id}`, `{error_code}`, `{duration_ms}`.
- **Typical value**: `"{atom_id} failed | error={error_code} duration_ms={duration_ms}"`.
- The *level* at which this logs is determined by `level_map`, not this template.

**`logging.level_map`**
- **What it is**: Map of error category (from L0 `error_categories`) to log level.
- **Purpose**: A NET error is usually transient (WARN). A SEC error needs attention (ERROR). Declared once.
- **Typical mapping**:
  - `VAL: INFO` — validation failures are routine.
  - `BUS: WARN` — business rule violations need attention.
  - `NET: WARN` — transient, will be retried.
  - `EXT: WARN` — third-party failure.
  - `SYS: ERROR` — infrastructure problem.
  - `SEC: ERROR` — security event.
  - `DAT: ERROR` — data integrity issue.
  - `CFG: ERROR` — misconfiguration.

**`tracing.span_name_template`**
- **What it is**: Template for distributed-trace span names around atom executions.
- **Template variables**: `{atom_id}`, `{owner_module}`.
- **Typical value**: `"{owner_module}.{atom_id}"`.

**`tracing.propagate`**
- **What it is**: Whether trace context flows across atom boundaries.
- Nearly always `true`. Set `false` only when an atom genuinely starts a new trace root (rare).

---

## Section 2: failure

### Purpose

Atoms declare what can go wrong (error codes). This section declares what to *do* when one is returned. Separating declaration from handling keeps atoms focused on their own logic.

### Fields

**`defaults.<error_category>.action`**
- **What it is**: Runtime response when an atom returns an error of this category.
- **Values**:
  - `return_to_caller` — propagate up; caller handles.
  - `retry` — reinvoke up to `retries` times with `backoff`.
  - `circuit_breaker` — open a breaker after repeated failures; fail fast until closed.
  - `dead_letter` — send input to a DLQ; return wrapped error.
  - `halt_and_alert` — stop the flow; page an operator.
- **Typical mapping**:
  - `VAL → return_to_caller` (caller's fault)
  - `BUS → return_to_caller` (rule violation, not transient)
  - `NET → retry` (transient)
  - `EXT → retry` or `circuit_breaker`
  - `SYS → halt_and_alert`
  - `SEC → halt_and_alert`
  - `DAT → halt_and_alert`
  - `CFG → halt_and_alert`

**`defaults.<error_category>.retries`**
- **What it is**: Max retry attempts. Required when `action` is `retry` or `circuit_breaker`. Must be omitted for other actions.
- **Typical**: 3 for NET, 2 for EXT.

**`defaults.<error_category>.backoff`**
- **What it is**: Backoff strategy for retries. Required when `action` is `retry` or `circuit_breaker`. Must be omitted for other actions.
- `exponential` is nearly always correct.

**`propagation.wrap_unexpected`**
- **What it is**: Whether uncaught exceptions get wrapped into a declared error code before propagation.
- Should be `true` unless you have a specific reason.

**`propagation.unexpected_code`**
- **What it is**: The error code used to wrap unexpected failures.
- Must exist as a key in L0 `errors`.
- **Typical**: a `SYS.SYS.999` catch-all.

---

## Section 3: audit

### Purpose

Some operations need audit trails. Atoms declare side effects (using markers from L0 `side_effect_markers`); this convention decides which markers trigger audit and what the entry contains. No per-atom audit config needed.

### Fields

**`triggers.side_effect_markers`**
- **What it is**: Side-effect markers that cause audit entry generation.
- **Purpose**: Atoms with any of these markers are automatically audited.
- **Typical value**: `[WRITES_DB, WRITES_FS, EMITS_EVENT, CALLS_EXTERNAL]`.
- All markers must exist in L0 `side_effect_markers`.

**`entry_shape.fields`**
- **What it is**: Field names every audit entry contains.
- **Typical value**: `[timestamp, atom_id, actor, input_digest, output_digest, error_code, duration_ms, trace_id]`.
- Note: `input_digest` and `output_digest` are hashes, not full payloads. Full payloads in audit are a compliance problem.

**`sink.kind`**
- **What it is**: Destination type for audit entries.
- `db_table` for a dedicated audit table, `event_stream` for a Kafka/EventBridge topic, `file` for structured log files.

**`sink.target`**
- **What it is**: Identifier of the sink — table name, topic name, or file path pattern.

---

## Section 4: security

### Purpose

Declare a single project-wide default posture and the role catalogue. Interface-kind-specific overrides live in L2, where interfaces are defined.

### Fields

**`default_posture.authentication`**
- **What it is**: Baseline authentication requirement for entry points.
- **Typical**: `required`. Entry points that diverge (scheduled jobs, public pages) override in L2.

**`default_posture.auth_methods`**
- **What it is**: Baseline allowed auth schemes.
- **Recognized values**: `bearer`, `api_key`, `oauth2`, `session`, `mtls`, `hmac`, `none`.
- L2 entry points may restrict further but not expand beyond this set.
- **Typical**: `[bearer, api_key]`.

**`default_posture.roles`**
- **What it is**: Baseline role requirement. Empty list = any authenticated caller.
- Most projects keep this empty and specify roles per-endpoint in L2.

**`roles.<role_name>`**
- **What it is**: The project's role catalogue. Every role reference anywhere in the project must exist here.
- **Typical roles**: `user`, `admin`, `service`, `auditor`.
- Each role's description should make the authorization model obvious.

### Strict layering note

L1 does not enumerate interface kinds (`api`, `event_consumer`, `cli`, `scheduled`, etc.). The default posture applies to all entry points. L2 modules override per-entry-point when needed, using their knowledge of which interface kind each entry point is.

### Resource authorization

Role checks answer "may this actor call this atom at all?" Resource authorization answers "may this actor mutate *this specific record*?" Both are needed for real systems — role alone lets any `user` edit any other `user`'s data.

**`resource_authorization.ownership_check_required_for_markers`**
- Side-effect markers that require an ownership check before the atom executes. Typically includes `WRITES_DB` so every mutation verifies the caller owns the target.
- Markers must exist in L0.6.

**`resource_authorization.ownership_field`**
- Conventional field name on owned entities that identifies the owner. `owner_id`, `user_id`, `tenant_id`, `account_id` — pick one and stay consistent.
- Entities that don't carry this field are implicitly unowned (global).

**`resource_authorization.admin_bypass`**
- When `true`, actors with role `admin` skip ownership checks. Useful for support/admin tools. When `false`, even admins must be explicit owners.

---

## Section 5: verification

### Purpose

Universal floor for atom verification. Kind-specific required sections belong to the kind's L3 schema.

### Fields

**`floors.min_property_assertions`**
- **What it is**: Minimum universal rules every atom must declare.
- **Typical**: 1. Some atoms have genuinely trivial logic.

**`floors.min_edge_cases`**
- **What it is**: Minimum boundary conditions every atom must enumerate.
- **Typical**: 2. Any atom has at least two (empty input, maximum input).

**`floors.min_example_cases`**
- **What it is**: Minimum concrete input/expected pairs.
- **Typical**: 1 or 2. Low enough that trivial atoms comply without ceremony.

### Why kind-specific floors are not here

Previously this section had per-kind floors and required sections. That required L1 to enumerate atom kinds, which is L3's business. Each kind's L3 schema declares its own required verification sections as part of the kind definition.

---

## Section 6: idempotency

### Purpose

Retries are only safe if operations are idempotent. This section declares how keys are enforced to make convention-driven retries safe.

### Fields

**`key_source.required_for_markers`**
- **What it is**: Side-effect markers that require an atom's input to include an idempotency key, unless the atom is also marked `IDEMPOTENT`.
- **Typical**: `[CALLS_EXTERNAL, WRITES_DB]`.
- All markers must exist in L0 `side_effect_markers`.

**`key_source.key_field`**
- **What it is**: Conventional name of the key field on atom inputs.
- **Typical**: `idempotency_key`. Pick one name and stay consistent across the project.

**`dedup.strategy`**
- **What it is**: How duplicate requests are detected on retry.
- `database`: dedup table indexed by key. Strongest guarantee.
- `cache`: short-TTL cache. Cheaper but can miss after TTL.
- `none`: valid only if no atoms need dedup.

**`dedup.ttl_sec`**
- **What it is**: How long a processed key is remembered.
- **Typical**: 86400 (24h) for cache; indefinite for database.

---

## Section 7: overrides

### Purpose

Atoms are expected to inherit L1 conventions without restating them. Occasionally an atom has a genuine reason to deviate — a payment atom that needs 5 retries instead of the default 3, or a health-check atom that logs at DEBUG instead of INFO.

This section declares the override mechanism so that deviations are structured, visible, and bounded.

### Fields

**`allowed_fields`**
- **What it is**: List of dotted paths to L1 fields that atoms may override.
- **Purpose**: Constrains the override surface. Atoms cannot override arbitrary conventions — only the fields listed here.
- **Typical value**:
  - `failure.defaults.<category>.action`
  - `failure.defaults.<category>.retries`
  - `failure.defaults.<category>.backoff`
  - `observability.logging.level_map.<category>`
  - `idempotency.dedup.strategy`
  - `idempotency.dedup.ttl_sec`

**`requires_justification`**
- **What it is**: Whether atoms must include a `justification` string with each override.
- **Typical**: `true`. Overrides without explanation rot into hidden tech debt.

### How atoms declare overrides (L3)

An atom's spec includes an optional `convention_overrides` block:

```yaml
convention_overrides:
  - field: "failure.defaults.NET.retries"
    value: 5
    justification: "Payment processor SLA allows up to 30s; 3 retries with exponential backoff only covers ~15s."
```

Each override must target a field listed in `overrides.allowed_fields`. If `requires_justification` is `true`, the `justification` field is mandatory.

---

## Common authoring mistakes

1. **Restating conventions in atoms.** If an atom's spec has an `observability` block, the convention should have covered it. Fix the convention, not the atom.
2. **Enabling retries without idempotency keys.** If NET retries are on, `idempotency.key_source.required_for_markers` must include the relevant markers.
3. **Too many verification floors.** Floors are floors. Ceilings come from atoms. Keep floors low.
4. **Typos in role references.** Every role used anywhere must exist in `security.roles`. Keep the catalogue small.
5. **Raw input in log templates.** Use `{input_summary}`, never raw fields.
6. **Specifying retries/backoff for non-retry actions.** These fields are conditional. Omit them when the action is `return_to_caller`, `dead_letter`, or `halt_and_alert`.
7. **Over-permissive override surface.** Keep `allowed_fields` narrow. If most atoms override the same field, change the convention instead.

---

## How atoms use L1

Atoms do not write any L1 fields. They:

1. Declare their `kind`, `side_effects` (using markers from L0), and the error codes they can return.
2. Declare their own `verification` content meeting or exceeding the floors.
3. Optionally override specific convention fields via `convention_overrides`, targeting only fields listed in `overrides.allowed_fields`.

Everything else — log format, log levels, retry behavior, audit entries, auth defaults, idempotency enforcement — is injected by the runtime from this convention file.
