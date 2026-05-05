# L0 Authoring Guide

This guide explains how to write a valid `L0_registry.yaml`. Every field in every section is described with its purpose, constraints, and common mistakes.

---

## Section 1: naming_ledger

The naming ledger is the grammar of your project. Every identifier used anywhere — module names, atom names, error codes, event names, constant names — must match the regex declared here for its class.

### Fields

**`module_id`**
- **What it is**: Regex that every module identifier must match.
- **Purpose**: Modules are the ownership boundary (L2). Every atom belongs to exactly one module, and atoms reference their module by id. A consistent module id format prevents typos and enables tooling.
- **Typical choice**: `^[A-Z]{3}$` — three uppercase letters, e.g., `PAY`, `USR`, `NTF`.
- **Common mistake**: Allowing module ids of variable length makes error codes (which embed the module id) inconsistent.

**`atom_id`**
- **What it is**: Regex for atom identifiers.
- **Purpose**: Atoms are the unit-of-behavior construct (L3). Every atom has a unique id referenced from orchestrations, journeys, and other atoms.
- **Typical choice**: `^atm\.[a-z]{3}\.[a-z_]+$` — prefix, module code (lowercase), underscored name, e.g., `atm.pay.charge_card`.

**`artifact_id`**
- **What it is**: Regex for artifact identifiers.
- **Purpose**: Artifacts are non-executing dependencies (datasets, weights, configs) declared in L3.
- **Typical choice**: `^art\.[a-z]{3}\.[a-z_]+$`.

**`flow_id`**
- **What it is**: Regex for orchestration identifiers (L4a).
- **Typical choice**: `^flow\.[a-z_]+$` — `flow` prefix, underscored name, e.g., `flow.process_order_payment`.
- **Note**: Flows are project-level, not owned by any single module. No module prefix in the ID.

**`journey_id`**
- **What it is**: Regex for journey identifiers (L4b).
- **Typical choice**: `^jrn\.[a-z_]+$` — `jrn` prefix, underscored name, e.g., `jrn.signup_flow`.
- **Note**: Journeys are project-level, not owned by any single module. A signup journey may span USR, PAY, and NTF without belonging to any.

**`type_id`**
- **What it is**: Regex for type identifiers declared in L0.4.
- **Typical choice**: `^reg\.[a-z]+\.[A-Z][a-zA-Z]+$` — `reg` prefix, namespace (usually a module code or `sys` for shared), PascalCase type name, e.g., `reg.pay.Charge`, `reg.sys.Email`.

**`error_code`**
- **What it is**: Regex for error codes.
- **Purpose**: Error codes are referenced from atom failure_matrix entries and appear in logs.
- **Typical choice**: `^[A-Z]{3}\.[A-Z]{3}\.\d{3}$` — module code, category code, three-digit number, e.g., `PAY.VAL.001`.
- **Important**: The first segment (module) must match a real module id.

**`event_name`**
- **What it is**: Regex for event names emitted by REACTIVE atoms or consumed by orchestrations.
- **Typical choice**: `^[a-z]+\.[a-z_]+$` — namespace plus action, e.g., `payment.completed`, `order.placed`.
- **Note**: Events are not catalogued in L0 — they are declared where they are emitted (L3 atoms) and consumed (L4a triggers). The naming pattern here validates their format.

**`constant_id`**
- **What it is**: Regex for constant identifiers declared in L0.5.
- **Purpose**: Ensures consistent naming for policy values referenced across modules.
- **Typical choice**: `^[A-Z][A-Z0-9_]+$` — SCREAMING_SNAKE_CASE, e.g., `MAX_LOGIN_ATTEMPTS`, `SESSION_TIMEOUT_SEC`.
- **Common mistake**: Using lowercase or mixed-case constant names that blend with variable names in implementation code.

**`policy_id`**
- **What it is**: Regex for policy identifiers declared in L2.B policy files.
- **Purpose**: Ensures consistent naming for cross-cutting rules applied per-module.
- **Typical choice**: `^pol\.[a-z]{3}\.[a-z_]+$` — `pol` prefix, module code (lowercase), underscored name, e.g., `pol.pay.require_admin_for_refunds`.

### Authoring notes

- Pick your patterns early and do not change them. All existing identifiers must be re-verified if a pattern changes.
- Keep patterns strict. A looser regex accepts more junk.
- Test your regexes against your intended identifier format before committing.

---

## Section 2: error_categories

A fixed map of 3-letter codes to their meaning. The category taxonomy is project-wide.

### Fields

**`<CATEGORY_CODE>: <description>`**
- The key is a 3-letter uppercase code.
- The value is a one-line human description.

### Standard categories to include

- `VAL` — Validation: input failed a contract check.
- `SYS` — Infrastructure: disk, memory, OS-level failure.
- `BUS` — Business Logic: a domain rule was violated.
- `SEC` — Security: authentication, authorization, injection.
- `NET` — Networking: upstream, DNS, timeout.
- `DAT` — Data: database constraint violation or corruption.
- `CFG` — Configuration: missing or malformed config.
- `EXT` — External: a third-party service returned failure.

Projects may add categories, but removing standard ones is discouraged because L1 conventions reference them.

---

## Section 3: errors

The full catalogue of error codes the project can produce.

### Fields per error entry

**`message`**
- **What it is**: Human-readable description of the error.
- **Purpose**: Surfaces in logs and in callers. Should be specific enough to diagnose from the message alone.
- **Common mistake**: Vague messages like "something went wrong" — if someone sees this in a log at 3am, they should know what happened.

**`category`**
- **What it is**: The 3-letter category code. Must exist as a key in `error_categories`.
- **Purpose**: The L1 Failure Convention uses category to decide default handling (NET retries, VAL returns immediately, etc.). Getting the category right is what makes convention-based handling correct.
- **Common mistake**: Using `SYS` for everything. Categorize precisely.

**`changelog`**
- Standard changelog entries documenting when and why this error code was added, renamed, or deprecated.

### When to add a new error code

- When an atom can fail in a way that callers must distinguish from other failures.
- When the L1 Failure Convention's per-category handling differs for this failure versus an existing one.

### When not to add a new error code

- For purely internal validation inside an atom (use pre-conditions, not a new error code).
- For variants that callers treat identically — one code is enough.

---

## Section 4: types

The catalogue of all data types. Two kinds: entities (records with fields) and enums (fixed value sets).

### Entity fields

**`kind: entity`**
- Required literal.

**`fields.<field_name>.type`**
- **What it is**: Either a primitive name or another `type_id`.
- **Allowed primitives**: `string`, `integer`, `number`, `boolean`, `bigint`, `bytes`, `timestamp`, `uuid`.
- **Purpose**: Nesting types by reference is how multi-field structures are built. An `Order` entity has a `customer` field of type `reg.usr.Customer`, which itself has `address` of type `reg.usr.Address`, etc.

**`fields.<field_name>.nullable`**
- **What it is**: Boolean. Whether the field may be absent/null.
- **Common mistake**: Marking things nullable to avoid thinking about defaults. Prefer a `default`.

**`fields.<field_name>.description`**
- Optional. Human description of what the field represents. Recommended for any field whose meaning isn't obvious from the name.

**`fields.<field_name>.default`**
- Optional. A default value used when the field is omitted at construction.

**`invariants`**
- Optional list. Pseudo-formal rules that must hold across fields of the entity. Examples:
  - `start_date <= end_date`
  - `total_cents == sum(line_items.*.amount_cents)`
- Validated at stage 5 (kind-specific invariant checks) by any atom that constructs or mutates the entity.

### Enum fields

**`kind: enum`**
- Required literal.

**`values`**
- List of allowed values. Typically uppercase strings, but can be integers.

### Circular references

An entity may reference another entity that (directly or transitively) references it, **only if** at least one edge in the cycle is nullable. Without this, instances of the cycle cannot be constructed.

---

## Section 5: constants

Named immutable values representing policy decisions.

### Fields

**`value`**
- The literal value. Must match the declared `type`.

**`type`**
- Either a primitive or a `type_id`. Usually a primitive.

**`description`**
- **What it is**: Human description.
- **Purpose**: Constants exist because the value is a policy decision. The description should explain *why* this value, not just what it is. `MAX_LOGIN_ATTEMPTS = 5` with description "Industry standard for balancing security and UX" is useful. Without the why, the constant is undercooked.

### When to use a constant

- The value is a policy decision (limits, timeouts, thresholds).
- The value is referenced in more than one place.
- The value might legitimately change and you want traceability.

### When not to use a constant

- Implementation details that shouldn't propagate (use in-atom literals).
- Values derived from others (compute them, don't duplicate).

---

## Section 6: side_effect_markers

The canonical vocabulary of side-effect labels. Atoms declare which markers apply to them; L1 conventions reference markers to drive audit, idempotency, and other cross-cutting behavior.

### Standard markers

- `PURE` — No observable side effects.
- `IDEMPOTENT` — Repeated invocation with the same input produces the same result with no additional effects.
- `READS_DB` — Reads from a database.
- `WRITES_DB` — Writes to a database.
- `READS_CACHE` — Reads from a cache layer.
- `WRITES_CACHE` — Writes to a cache layer.
- `READS_FS` — Reads from the filesystem.
- `WRITES_FS` — Writes to the filesystem.
- `READS_ARTIFACT` — Reads an L3 artifact (dataset, model weights, config bundle, prompt template, localization file).
- `EMITS_EVENT` — Publishes an event to a bus or stream.
- `CALLS_EXTERNAL` — Makes a call to an external service.
- `READS_CLOCK` — Depends on the current time.

### Authoring notes

- Projects may add markers beyond the standard set. All markers used in L1 conventions or L3 atom specs must exist here.
- An atom may have multiple markers. `WRITES_DB` and `EMITS_EVENT` on the same atom is common.
- `PURE` and `IDEMPOTENT` are constraints, not effects. An atom marked `PURE` must not also carry any other marker, including `READS_CLOCK` — reading the clock is observable state and breaks purity.

---

## Section 7: external_schemas

Minimal declarations of third-party services. Full request/response shapes live in artifacts (L3) or are pulled from live sources like OpenAPI specs.

### Fields

**`provider`**
- Human name of the third-party service.

**`base_url`**
- The root URL. Per-endpoint paths are specified in atoms that call the service, not here.

**`auth_method`**
- One of: `bearer`, `hmac`, `oauth2`, `api_key`, `mtls`, `none`.
- Actual credentials (keys, secrets) are declared in the module's L2 access permissions, never in L0.

### Authoring note

Keep this minimal. L0.7 is a registry of *which* services exist, not *how* to talk to them in detail. The details belong with the atoms that use them.

---

## Stability markers

Types, enums, errors, constants, and external_schemas may declare an optional `stability` field with one of three values:

- `stable` — production-ready. Breaking changes require a major version bump and a deprecation cycle. Default when `stability` is omitted.
- `beta` — usable but subject to change. Consumers should expect breaking changes without a full deprecation cycle.
- `deprecated` — scheduled for removal. New code must not reference this. Existing consumers should migrate.

Changelog `change_type: deprecated` and the `stability: deprecated` field are complementary: the changelog records when the decision was made; the `stability` field exposes current status without needing to read the changelog.

---

## Common authoring mistakes

1. **Changing naming_ledger patterns after identifiers exist.** Breaks everything that referenced old names. Pick patterns early.
2. **Over-categorizing errors.** 15 categories is too many. 8 is plenty.
3. **Using vague error messages.** Write messages assuming someone is reading them in a log with no context.
4. **Skipping field descriptions on entities.** A year later, nobody remembers what `flags: integer` meant.
5. **Not versioning.** Every change to L0 gets a changelog entry. Git history is not a substitute — changelogs capture intent.
6. **Adding side-effect markers without justification.** The standard set covers most cases. Only add a marker if L1 conventions or L3 atoms need to distinguish a new class of effect.
