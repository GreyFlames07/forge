# L2 Authoring Guide

L2 defines the modules that partition your system. Each module owns atoms and artifacts, exposes interfaces, and controls its own boundaries.

---

## Module Spec

### Section 1: Identity

**`id`**
- Must match `naming_ledger.module_id`.
- Typically 3 uppercase letters: `PAY`, `USR`, `NTF`, `INV`.
- This code appears in atom IDs (`atm.pay.*`), error codes (`PAY.VAL.001`), and everywhere the module is referenced.

**`name`**
- Human-readable module name: "Payments", "User Management", "Notifications".

**`description`**
- **This is critical.** The description is the primary documentation of what the module owns and why it exists as a separate boundary.
- Write it for a new team member who needs to understand the system in 30 seconds.
- Should answer: what domain does this module cover, what are its key responsibilities, why is it separated from adjacent modules.
- Be comprehensive. This is not a one-liner.

---

### Section 2: Tech Stack

**`language` / `language_version`**
- The language atoms in this module are implemented in.
- `language_version` must be a pinned version string (e.g., `"5.4"`, `"3.11.2"`, `"20.x"`). Bare names like `"latest"` are rejected.
- Different modules can use different languages. A Python ML module alongside a TypeScript API module is normal and expected.

**`runtime` / `runtime_version`**
- The execution environment: `node`, `python`, `jvm`, `go`, `wasm`, etc.
- `runtime_version` follows the same validation as `language_version`.

**`frameworks`**
- Major frameworks with pinned versions using `name@version` format: `[nestjs@10, prisma@5]`, `[fastapi@0.100, sqlalchemy@2]`.
- The validator enforces the pattern `^[a-z0-9_\-/.]+@[\w.\-]+(\.x)?$`. Unpinned entries (missing `@version`) are rejected.

**`mandatory_libraries`**
- Libraries every atom in this module depends on: `[stripe-node@14]`, `[numpy@1.26]`.
- Same format and validation as `frameworks`.

### Uniform version rigor

All four version fields (`language_version`, `runtime_version`, framework versions, library versions) are validated against the same pattern. Version pinning is non-negotiable — unpinned dependencies drift and break builds.

### When to split modules

Split when two groups of atoms have different tech stacks, different persistence, different access permissions, or different dependency sets. If two atoms share everything, they belong in the same module. If a module owns 50+ atoms with diverse concerns, it is probably two modules.

---

### Section 3: Owned Inventory

**`owned_atoms`**
- Exhaustive list of atom IDs this module owns.
- Every atom in L3 must appear in exactly one module's list.
- These are reference IDs only. Atom specs live in their own L3 files.

**`owned_artifacts`**
- Same for artifacts.

### Common mistake

Forgetting to add a new atom here when creating it in L3. The validator catches this — orphan atoms fail stage 4.

---

### Section 4: Persistence Schema

**`datastores`**
- Each entry maps a logical datastore name to an L0 entity type from L0.4, plus a `form` declaring the storage shape.
- The entity type defines the shape of each stored item (columns / document fields / value structure, types, constraints). The datastore `name` is the logical identifier used across the spec.
- The `form` field is storage-neutral and describes the *shape* of persistence: `relational` (SQL tables), `document` (JSON-ish documents), `key_value` (single-key access), `column_family` (wide-column), `graph` (nodes + edges), `search` (full-text indexes), or `time_series` (append-only time-indexed).
- The actual engine (Postgres vs. Aurora vs. DynamoDB vs. Mongo) is declared separately in `tech_stack.managed_services`. This separation means swapping engines doesn't change the datastore declaration — only the managed-services entry.
- **The entity type must be a `kind: entity` type, not an enum.** Enum types are fixed value sets, not item shapes. Mapping a datastore to an enum fails validation.
- Examples: `{name: charges, type: reg.pay.Charge, form: relational}` or `{name: user_sessions, type: reg.usr.Session, form: key_value}`.

**`storage_buckets`**
- Object storage (S3, GCS, Azure Blob, etc.) this module owns. Optional. List bucket names or prefixes.

**`caches`**
- Cache namespaces (Redis key prefixes, Memcached namespaces) this module owns. Optional. Use this for ephemeral caching layers, not primary stores — a Redis instance used as the sole store for something goes under `datastores` with `form: key_value`.

**`ownership`**
- Applies uniformly to **all three** resource types (datastores, buckets, caches) in this section.
- `exclusive`: only this module reads and writes these resources. Strongest isolation. Preferred.
- `shared`: multiple modules access these resources. Requires `shared_with` listing the other modules.
- Use shared sparingly — it couples modules and complicates reasoning about data ownership.
- If your module needs exclusive datastores but shared caches, split the cache into a separate module with `shared` ownership.

**`shared_with`**
- Required when `ownership: shared`. Lists every module that also accesses these resources.
- Both the owning module and the sharing module should declare the relationship in their own specs.

---

### Section 5: Interface

**`entry_points`**
- Each entry binds an external trigger to an internal atom, flow, or journey.
- The `kind` field determines which additional fields are required.

**`kind`**
- The type of external trigger. One of: `api`, `event_consumer`, `cli`, `scheduled`, `websocket`, `grpc`, `web_journey_entry`, `mobile_journey_entry`.

**Kind-specific fields:**

- `api`: requires `endpoint` (the URL path) and `method` (one of `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`). Methods outside this set are rejected.
- `grpc`: requires `endpoint` (the service/method path).
- `event_consumer`: requires `event` (the event name from L0's event_name pattern).
- `scheduled`: requires `schedule` (a cron expression; 5-field `m h dom mon dow` or 6-field with seconds). Validated for syntactic correctness.
- `websocket`: requires `endpoint`.
- `cli`: no kind-specific fields. Command strings, argument parsing, and flag shapes are implementation-specific and do not belong in the schema.
- `web_journey_entry`: requires `endpoint` (the URL that starts the journey).
- `mobile_journey_entry`: no kind-specific fields.

**`invokes`**
- What this entry point triggers internally.
- Can be an atom ID (direct invocation), a flow ID (orchestration), or a journey ID (user-facing path).
- For web UIs: entry points of kind `web_journey_entry` invoke journeys. The journey manages which screens render.

**`request_type` / `response_type`**
- Optional. The input and output shape, referencing L0.4 types.
- Most useful for `api` and `grpc` kinds.

**`security`**
- Optional override block.
- When absent: inherits L1 `default_posture`.
- When present: overrides authentication, auth_methods, and/or roles for this specific entry point.
- Use for entry points that diverge from project default: scheduled jobs that skip auth, public signup pages, admin-only endpoints.
- `auth_methods` may restrict from L1's set but not expand beyond it.
- All `roles` referenced must exist in L1 `security.roles`.

### Note on event names

Events are not catalogued in L0 — only their naming pattern is declared. A typo'd event name in an `event_consumer` entry point will pass validation as long as the typo matches the regex. Cross-check event names against emitters (L3 REACTIVE atoms) during review.

### Kind-specific field hygiene

Each interface kind has a fixed set of required fields and a fixed set of irrelevant fields. An `api` entry point must not declare `event` or `schedule`; an `event_consumer` must not declare `endpoint` or `method`. The validator rejects entries that declare fields inappropriate to their kind — not just missing required fields.

### Endpoint uniqueness across modules

Endpoints are a project-global namespace. Two modules cannot both declare `POST /payments/charge`, even if they're logically separate concerns. The validator enforces uniqueness across all modules for `(endpoint, method)` on api entries, for `endpoint` alone on grpc/websocket/web_journey_entry.

---

### Section 6: Access Permissions

**`env_vars`**
- Environment variables this module may read. `STRIPE_API_KEY`, `DATABASE_URL`, etc.

**`filesystem`**
- Filesystem paths this module may access. Usually empty for API services.

**`network`**
- External domains this module may reach. `api.stripe.com`, `smtp.sendgrid.com`.
- A module that doesn't list a domain cannot call it. Makes external dependencies explicit.

**`secrets`**
- Secret manager keys this module may access.

**`external_schemas`**
- L0.7 external schema IDs this module integrates with. `[stripe, sendgrid]`.
- Establishes the registered link between this module and L0's external service catalogue. If a module calls Stripe, `stripe` must appear here AND in L0.7. The `network` domain and `secrets` whitelists don't create the registered link — this field does.
- Required for validators and tooling to reason about the module's third-party surface.

### Purpose

Capability whitelist. Anything not listed is forbidden. Prevents accidental external dependencies and makes each module's runtime surface explicit and reviewable.

---

### Section 7: Dependency Whitelist

**`modules`**
- Other module IDs this module may call atoms from.
- If module PAY calls `atm.usr.fetch_customer` but `USR` is not in PAY's whitelist, validation fails at stage 4.

### No acyclicity constraint

Modules may have mutual dependencies (PAY ↔ USR is legal). Saga-style orchestration and cross-reference lookups both need this. Review cross-module loops manually — they are allowed but should be intentional.

### Common mistake

Forgetting to whitelist a module when adding a cross-module call. The validator catches this.

---

### Section 8: Policies

**`policies`**
- List of policy IDs this module opts into.
- Policies are defined in separate L2.B files.
- All atoms in this module that match a policy's `applies_when` predicate inherit the policy's mandatory behavior.
- Unlike L1 conventions (universal, automatic), policies are targeted and opt-in per module.

---

### Section 9: Changelog

Standard changelog. Changes to modules are architectural — new interfaces, new persistence, changed permissions all deserve entries.

---

## Policy Spec

### Purpose

Policies handle targeted cross-cutting rules too specific for L1 conventions but too repetitive to declare per-atom.

- L1 conventions: universal project defaults (every atom logs, every NET error retries).
- Policies: specific rules for specific modules (refunds need admin, ML atoms log confidence).

### Fields

**`id`**
- Must match `naming_ledger.policy_id`.
- Typical pattern: `pol.<module>.<name>`, e.g., `pol.pay.require_admin_for_refunds`.

**`name` / `description`**
- Human-readable. Description should explain *why* this policy exists, not just what it does. Policies exist because of business or compliance requirements — name the requirement.

**`applies_when`**
- Predicate over atom properties using pseudo-formal syntax.
- Available properties: `atom.id`, `atom.side_effects`, `atom.owner_module`.
- Side-effect markers referenced must exist in L0.6.
- Examples:
  - `atom.id matches "atm.pay.refund_*"` — targets refund atoms specifically.
  - `atom.side_effects contains WRITES_DB` — targets all state-mutating atoms.
  - `atom.side_effects contains CALLS_EXTERNAL AND atom.owner_module == "PAY"` — compound predicate.

**`mandatory_behavior.before`**
- Pseudo-formal action injected before atom logic. Optional.
- Example: `assert actor.role == admin else raise SEC.SEC.003`.
- Any error code referenced must exist in L0.3.

**`mandatory_behavior.after_success`**
- Injected after successful return. Optional.
- Example: `emit billing.refund_completed with { atom_id, amount, actor }`.

**`mandatory_behavior.after_failure`**
- Injected after error return. Optional.
- Example: `log to security_alerts with { atom_id, error_code, actor }`.

**`opt_out.allowed`**
- `false` for hard security policies. No atom can escape.
- `true` for advisory policies where some atoms may legitimately not need the rule.

**`opt_out.requires_justification`**
- If `true`, atoms opting out must provide a written justification string. Creates an audit trail for exceptions.

---

## Common authoring mistakes

1. **Module too big.** If a module owns 50+ atoms with diverse concerns, split it. The trigger: atoms within the module have different persistence, different permissions, or different tech stacks.
2. **Module too small.** One atom per module is over-isolation. Group atoms that share persistence and evolve together.
3. **Shared persistence without shared_with.** If two modules write the same table, both must declare `ownership: shared` and list each other.
4. **Missing dependency whitelist entries.** Validator catches cross-module calls to unlisted modules, but maintain the list proactively.
5. **Orphan policies.** A policy nobody references is dead code. Validator warns on these.
6. **Security overrides that expand auth_methods.** Entry points may restrict from L1's set, never expand it.
7. **Vague module descriptions.** "Handles stuff" is not a description. A new team member should understand the module's purpose, responsibilities, and why it's a separate boundary from reading the description alone.
8. **Unpinned framework versions.** `[nestjs]` fails validation. Always include `@version`.
9. **CLI argument shapes in the schema.** Keep CLI entry points abstract. Command strings and flags are implementation concerns.
