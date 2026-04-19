# The Six-Layer Spec Framework

## What It Is

A pseudo-formal specification language for agentic software development. The spec is canonical — code is a compilation target produced by mechanical translation from validated specs. The framework exists to eliminate interpretation: given the same spec, any agent produces equivalent code.

## Core Thesis

Atoms (the unit of behavior) contain only value-add logic — dependencies, signatures, interactions, and logic unique to that atom. Everything else (logging, failure handling, audit, auth, verification floors, idempotency) is declared once at the project level via conventions and inherited automatically. This is a context management strategy: specs stay focused on what matters, frame concerns are handled globally.

## Strict Layering Rule

Higher-numbered layers may reference lower-numbered ones, never the reverse. No layer enumerates another layer's internal taxonomy.

---

## The Six Layers

### L0 — Registry

**Path**: `src/templates/L0/`

The definitional truth. Every name, type, error code, event, constant, side-effect marker, and external service reference used anywhere in the project resolves to a single entry here. L0 is the vocabulary the entire system is built from.

**Contains**:
- **Naming ledger** (L0.1) — regex patterns per entity class (module, atom, artifact, flow, journey, type, error, event, constant, policy). Ten entity classes total. Flows and journeys have no module prefix — they are project-level.
- **Error categories** (L0.2) — fixed 3-letter codes to meaning (VAL, SYS, BUS, SEC, NET, DAT, CFG, EXT).
- **Error dictionary** (L0.3) — code → message + category, with changelog.
- **Type registry** (L0.4) — entities (records with fields, invariants) and enums (fixed value sets). Primitives: `string`, `integer`, `number`, `boolean`, `bigint`, `bytes`, `timestamp`, `uuid`.
- **Constants** (L0.5) — named policy values (limits, timeouts, thresholds) with type and description.
- **Side-effect markers** (L0.6) — canonical vocabulary of effect labels (`PURE`, `IDEMPOTENT`, `READS_DB`, `WRITES_DB`, `READS_ARTIFACT`, `EMITS_EVENT`, `CALLS_EXTERNAL`, `READS_CLOCK`, etc.). Used by L1 conventions and L3 atoms.
- **External schemas** (L0.7) — minimal third-party service references (provider, base URL, auth method).

**Key rules**:
- All seven sections mandatory.
- Every identifier across the system must match its naming_ledger regex.
- Circular type references require at least one nullable edge.
- Events are not catalogued here — they are declared where emitted (L3) and consumed (L4a). The naming pattern validates format.

---

### L1 — Conventions

**Path**: `src/templates/L1/`

Project-wide defaults for frame logic. Declares how the system behaves by default so that atoms don't restate boilerplate. L1 uses only universal framework vocabulary (error categories, side-effect markers, log levels from L0) — it does not enumerate atom kinds or interface kinds.

**Contains**:
- **Observability** (L1.1) — log templates (`on_entry`, `on_success`, `on_failure`), `default_level` for non-failure logs, `level_map` for failure logs (keyed by error category), trace span config.
- **Failure handling** (L1.2) — per error category: action (`return_to_caller`, `retry`, `circuit_breaker`, `dead_letter`, `halt_and_alert`), retries and backoff (conditional on retry actions only), unexpected-error wrapping.
- **Audit** (L1.3) — which side-effect markers trigger audit entries, entry field shape, sink destination.
- **Security** (L1.4) — default authentication posture, recognized auth methods (`bearer`, `api_key`, `oauth2`, `session`, `mtls`, `hmac`, `none`), role catalogue, and `resource_authorization` for per-record ownership checks.
- **Verification floors** (L1.5) — minimum property assertions, edge cases, and example cases every atom must meet. Kind-specific floors belong to L3.
- **Idempotency** (L1.6) — which markers require idempotency keys, dedup strategy and TTL.
- **Overrides** (L1.7) — declares which convention fields atoms may override, and whether justification is required.

**What L1 is not**: deployment, rate limiting, and event delivery semantics are platform concerns that belong in **L5 Operations**, not here. L1 stays focused on atom-level frame logic.

**Key rules**:
- All seven sections mandatory.
- All cross-references to error categories and side-effect markers resolve against L0.
- `retries` and `backoff` fields must be omitted for non-retry actions.
- Atoms inherit all conventions by default; overrides are opt-in, bounded by `overrides.allowed_fields`.

---

### L2 — Architecture

**Path**: `src/templates/L2/`

Modules — the ownership and boundary units of the system. Each module ships as one file at `modules/<MODULE_ID>.yaml`. Policies ship as separate files at `policies/<POLICY_ID>.yaml`.

**Contains** (per module):
- Identity (id matching L0 `module_id`, name, description).
- Tech stack (language, runtime, frameworks with pinned `name@version` format; optional `compute` overriding the project-wide default from L5 and optional `managed_services` declaring infrastructure-level cloud dependencies).
- Owned atoms and artifacts (reference lists; defs live in L3).
- Persistence schema (storage-neutral datastores mapped to L0 entity types with a `form` field declaring the storage shape — `relational`, `document`, `key_value`, `column_family`, `graph`, `search`, or `time_series` — plus storage buckets and caches; single `ownership` setting applies to all three). The storage engine itself is declared separately in `tech_stack.managed_services`, so the same spec works across engines.
- Interface (entry points binding external triggers to atoms/flows/journeys). Recognized kinds: `api`, `event_consumer`, `cli`, `scheduled`, `websocket`, `grpc`, `web_journey_entry`, `mobile_journey_entry`. Per-entry security overrides inherit from L1 `default_posture`. CLI entry points stay abstract — no command strings or flag specs.
- Access permissions (env vars, filesystem, network, secrets whitelists).
- Dependency whitelist (other modules this one may call). Cycles are permitted — review manually.
- Applied policies (policy IDs, defined in separate L2.B files).

**Policies** (L2.B) provide targeted cross-cutting rules narrower than L1 conventions:
- `applies_when` predicate over atom properties (side-effect markers, id patterns, owner module).
- `mandatory_behavior` hooks: `before`, `after_success`, `after_failure`.
- `opt_out` controls with optional justification requirement.

Interface-kind-specific security overrides live at L2 because L2 is where interfaces are defined.

---

### L3 — Units of Behavior

**Path**: `src/templates/L3/`

Two sibling constructs:

**Atoms** — the smallest unit of specified behavior. Each atom has:
- Shared fields: `id`, `kind`, `owner_module`, `description`, `verification`, `changelog`.
- Discriminated `spec` block whose shape is determined by `kind`.
- Optional `convention_overrides` block targeting L1 convention fields (listed in L1.7 `overrides.allowed_fields`).
- Optional `policy_overrides` block opting out of L2 policies applied to the owning module.

**Four atom kinds**: PROCEDURAL, DECLARATIVE, COMPONENT, MODEL. Each kind has its own mandatory fields, validation rules, and verification requirements. Single-kind only — no `secondary_kind`. If an atom seems to need two kinds, decompose it.

- **PROCEDURAL** — executes steps, returns a value. Covers functions, handlers, CLI commands, API logic, event processors, pipeline stages, protocol handlers, solvers. The default.
- **DECLARATIVE** — describes desired state; idempotent. Covers database schemas, Terraform resources, config files, CSS.
- **COMPONENT** — renders UI, holds local state, emits events. Covers React/Vue/Svelte components, screens, TUI widgets. Composes only other COMPONENT atoms.
- **MODEL** — probabilistic. Has acceptable bounds rather than exact outputs. Covers ML classifiers, prediction models. Requires a deterministic `fallback` (PROCEDURAL or DECLARATIVE).

**Previously-separate kinds** (REACTIVE, PIPELINE, PROCESS, PROTOCOL, SOLVER) are now expressed as PROCEDURAL atoms with specific patterns, with stream/loop/state-machine scaffolding in L2 interface or L4a orchestration.

**Artifacts** — non-executing dependencies: datasets, model weights, configs, prompt templates, localization files. Each declares format, schema, provenance, storage, consumers, and retention policy.

---

### L4 — Flows

**Path**: `src/templates/L4/`

Two sibling constructs at the same level — peers with different concerns.

**L4a — Orchestrations** (`flows/<FLOW_ID>.yaml`). Internal coordination of atoms. No user concept. **Project-level, not module-owned** — flow IDs do not embed a module prefix (e.g., `flow.process_order_payment`, not `flow.pay.*`).
- Trigger (event, invocation, scheduled, manual).
- Transaction boundary (saga, acid, none).
- Step sequence — each step invokes an atom or nested orchestration, with `with:` bindings referencing `trigger.*` or `<step>.output.*`.
- Per-step error handling: `HALT`, `HALT_AND_EMIT`, `RETRY(max=n)`, `GOTO`, `CONTINUE`, `COMPENSATE_AND_HALT`.
- Compensation atoms for saga rollback (explicit `null` when a step needs none).
- State transitions (flow-level observable state changes, optional event emits).
- Verification criteria per outcome scenario.

**L4b — Journeys** (`journeys/<JOURNEY_ID>.yaml`). External-facing paths. **Project-level, not module-owned** — journey IDs do not embed a module prefix (e.g., `jrn.signup_flow`, not `jrn.usr.*`). A journey may span many modules.
- Surface (web_ui, mobile_ui, api, cli, conversation, email_sequence).
- Entry point (from, initial_state, preconditions) — aligned with an L2 interface entry point.
- States and exit_states (at least one exit state reachable).
- Handlers per state — COMPONENT atom for UI surfaces, PROCEDURAL for api/cli/conversation/email.
- Transitions: from → on (event/action/`"auto"`) → optional invoke → to, with per-error actions (`STAY`, `GOTO state=<name>`, `ABORT`) and optional guards.
- `with:` bindings reference `trigger.*`, `handler.*`, `previous_state.*`, `event.*`.
- Verification criteria per scenario include the state path traversed.

**Both reference each other.** Journey transitions can invoke orchestrations; orchestrations can be triggered by journey-emitted events.

---

### L5 — Operations

**Path**: `src/templates/L5/`

Project-wide platform guarantees and runtime behavior. One file per project at `operations/L5_operations.yaml`. Separate from L1 because change cadence and ownership differ — L1 conventions are stable and owned by the architecture author; L5 operations evolve with platform tooling and are typically owned by ops / platform teams.

**Contains**:
- **Deployment** (L5.1) — optional `platform` sub-block (cloud, primary/additional regions, default compute model — all free-form strings), environment list (`[dev, staging, prod]`), default release strategy (`rolling | canary | blue_green | recreate`), canary traffic weights, rollback policy (automatic conditions + manual allowed flag).
- **Rate limiting** (L5.2) — default requests-per-minute and burst, per-auth-method overrides, scope (`per_actor | per_ip | per_api_key | global`).
- **Event semantics** (L5.3) — delivery guarantee (`at_most_once | at_least_once | exactly_once`), ordering (`fifo_per_key | unordered`), default parallelism, ordering key field.
- **Observability** (L5.4, optional) — observability stack declaration (e.g., `prometheus-alertmanager-grafana`); project-wide SLA defaults (latency p99, error budget, trace sample rate); per-module overrides with metric declarations (counter/gauge/histogram/summary), alert rules (PromQL expressions, severity, evaluation window), and trace sample rates; per-atom SLA and trace overrides for atoms with materially different SLA targets than their module. Used by `forge-validate` Phase 4 for live SLA assertion and metrics presence checks. The planned `forge-observe` skill will generate Prometheus rules, AlertManager config, and Grafana dashboard scaffolds from this block.

The `deployment.platform` sub-block is optional — include only the parts that are decided. It interacts with L2: a module's `tech_stack.compute` overrides `platform.default_compute`, and a module's `tech_stack.managed_services` declares infrastructure-level cloud dependencies beyond API-level `external_schemas`.

L2 entry points and modules may override L5 defaults where needed, following the same override discipline L1 uses.

---

## Cross-Layer Reference Direction

```
L0  ←  L1  ←  L2  ←  L3  ←  L4 (L4a / L4b)  ←  L5
```

Arrows show "references." L1 references L0. L2 references L0 and L1. L3 references L0, L1, and L2. L4 references everything below it. L5 references L0, L1, and L2 (for auth method names, side-effect markers, etc.) but not L3 or L4 specifics. No reverse references.

L4a and L4b are peers — they may reference each other (journeys invoke orchestrations; orchestrations are triggered by journey events).

---

## Validation Pipeline

Every spec passes five stages before acceptance:

1. **Syntactic parse** — valid YAML.
2. **Base schema validation** — all mandatory sections and fields present, correct types.
3. **Discriminated sub-schema validation** — for atoms (L3): kind selects which fields are mandatory.
4. **Cross-reference validation** — all identifiers resolve, relationships are legal (error codes exist in L0, markers exist in L0, roles exist in L1, modules exist in L2, atoms exist in L3).
5. **Kind-specific invariant checks** — semantic rules per kind (e.g., PROCEDURAL logic paths must terminate via RETURN, COMPONENT composes only COMPONENT atoms, MODEL must declare a PROCEDURAL/DECLARATIVE fallback and bounds_verification, PURE atoms must not carry effect markers, circular type references require nullable edges).

No spec proceeds to implementation until all five stages pass.

---

## File Structure

Two parallel trees under `src/`:

- **`templates/`** — schemas and guides only. Flat per layer: `templates/L<n>/L<n>_*.schema.md` and `templates/L<n>/L<n>_*.guide.md`.
- **`example/`** — a mock project laid out exactly as the schemas specify. No layer folders here — the directory structure matches what a real project using this framework would produce.

```
forge/
├── docs/
│   └── framework-overview.md
└── src/
    ├── templates/
    │   ├── L0/
    │   │   ├── L0_registry.schema.md
    │   │   └── L0_registry.guide.md
    │   ├── L1/
    │   │   ├── L1_conventions.schema.md
    │   │   └── L1_conventions.guide.md
    │   ├── L2/
    │   │   ├── L2_architecture.schema.md
    │   │   └── L2_architecture.guide.md
    │   ├── L3/
    │   │   ├── L3_behavior.schema.md
    │   │   └── L3_behavior.guide.md
    │   ├── L4/
    │   │   ├── L4_flows.schema.md
    │   │   └── L4_flows.guide.md
    │   └── L5/
    │       ├── L5_operations.schema.md
    │       └── L5_operations.guide.md
    └── example/
        ├── L0_registry.yaml                # singleton
        ├── L1_conventions.yaml             # singleton
        ├── L2_modules/
        │   ├── PAY.yaml
        │   ├── USR.yaml
        │   ├── INV.yaml
        │   ├── NTF.yaml
        │   ├── ORD.yaml
        │   └── UI.yaml
        ├── L2_policies/
        │   └── pol.pay.require_admin_for_refunds.yaml
        ├── L3_atoms/
        │   ├── atm.pay.charge_card.yaml
        │   ├── atm.pay.handle_order_event.yaml
        │   ├── atm.pay.charges_schema.yaml
        │   ├── atm.usr.signup_email_screen.yaml
        │   └── atm.usr.email_validity_classifier.yaml
        ├── L3_artifacts/
        │   └── art.usr.labeled_emails_v3.yaml
        ├── L4_flows/
        │   └── flow.process_order_payment.yaml
        ├── L4_journeys/
        │   └── jrn.signup_flow.yaml
        └── L5_operations.yaml              # singleton
```

**Directory convention**: singleton layer files (`L0_registry.yaml`, `L1_conventions.yaml`, `L5_operations.yaml`) sit at the project root with the layer prefix in the filename. Multi-entity layers get a prefixed directory (`L2_modules/`, `L3_atoms/`, etc.) — the layer is always visible in the path without inventing pedagogical layer folders around the singletons.

Each layer contributes two files in `templates/` (schema + guide) and zero or more files in `example/` at the canonical path the schema specifies.

---

## Scope

**In scope**: Backend services, full-stack web, CLIs, ETL, ML inference, trading systems, smart contracts, infrastructure-as-code, games, real-time/protocol systems, optimization systems.

**Out of scope**: Register-level firmware, formal verification artifacts, creative/generative content, exploratory research code.
