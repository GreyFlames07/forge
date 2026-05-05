# L2 — Architecture Schema

**Purpose**: Modules — ownership, boundaries, interfaces, permissions, policies.

**Scope**: Per-module.

**File format**: YAML. One file per module at `L2_modules/<MODULE_ID>.yaml`. Policies at `L2_policies/<POLICY_ID>.yaml`.

---

## L2.A — Module Spec

### Top-level structure

```yaml
module:
  id:                   <module_id>
  name:                 <string>
  description:          <string>

  tech_stack:           { ... }
  owned_atoms:          [...]
  owned_artifacts:      [...]
  persistence_schema:   { ... }
  interface:            { ... }
  access_permissions:   { ... }
  dependency_whitelist: { ... }
  policies:             [...]
  changelog:            [...]
```

All sections mandatory. Empty sections declared as `[]` or `{}`.

---

### L2.A.1 — Identity

```yaml
module:
  id:          <module_id>
  name:        <string>
  description: <string>
```

`id` must match `naming_ledger.module_id`. `description` must be comprehensive and human-readable — it is the primary documentation of what this module owns and why it exists as a boundary.

---

### L2.A.2 — Tech Stack

```yaml
tech_stack:
  language:            <string>
  language_version:    <version_string>
  runtime:             <string>
  runtime_version:     <version_string>
  frameworks:          [<name@version>, ...]
  mandatory_libraries: [<name@version>, ...]
  compute:             <string>                    # optional
  managed_services:                                # optional
    - service:  <string>
      purpose:  <string>
  source_root:         <string>                    # optional; default src/<mod_lower>/
  schema_tool:         <string>                    # optional; for DECLARATIVE database_schema targets
  iac_tool:            <string>                    # optional; for DECLARATIVE infrastructure targets
```

Version validation (applies uniformly to `language_version`, `runtime_version`, and the version portion of `frameworks` / `mandatory_libraries`):

- Must be non-empty.
- Must match `^[\w.\-]+(\.x)?$` (semver, partial semver, `20.x`, `3.11.2`, etc.).
- Bare names like `latest` are rejected.

`frameworks` and `mandatory_libraries` entries must match the pattern `^[a-z0-9_\-/.]+@[\w.\-]+(\.x)?$` (name, `@`, version).

`compute` is optional. When present, it declares this module's compute model (e.g., `lambda`, `ecs-fargate`, `cloud-run`, `kubernetes`, `azure-functions`). When absent, the module inherits `L5.deployment.platform.default_compute`. Free-form string — no fixed enum — because compute model names vary across clouds and platforms.

`managed_services` is optional. When present, it declares the cloud-managed or third-party platform services this module depends on beyond `access_permissions.external_schemas` (which covers API-level integrations like Stripe). `managed_services` covers infrastructure-level dependencies — databases, queues, storage, search — that the module uses but doesn't call as API services. Each entry has a free-form `service` identifier (e.g., `aws-rds`, `aws-sqs`, `azure-sql`, `gcp-bigquery`, `mongodb-atlas`) and a one-line `purpose`.

Different modules may run different stacks within the same project.

---

### L2.A.3 — Owned Inventory

```yaml
owned_atoms:     [<atom_id>, ...]
owned_artifacts: [<artifact_id>, ...]
```

Reference lists (IDs only). Actual definitions live in L3 files. Every atom and artifact in the project must appear in exactly one module's owned inventory.

---

### L2.A.4 — Persistence Schema

```yaml
persistence_schema:
  datastores:
    - name:  <string>
      type:  <type_id>
      form:  relational | document | key_value | column_family | graph | search | time_series
  storage_buckets: [<string>, ...]
  caches:          [<string>, ...]
  ownership:       exclusive | shared
  shared_with:     [<module_id>, ...]
```

`datastores`, `storage_buckets`, and `caches` are each optional. `shared_with` required only when `ownership: shared`. Each datastore entry maps a logical name to an L0 entity type (which defines the shape of each stored item) and declares the storage form.

The `form` field is storage-neutral — it describes the *shape* of the persistence, not the specific engine. The engine itself is declared in `tech_stack.managed_services` (e.g., `aws-rds` for a `relational` store, `aws-dynamodb` for `key_value`, `mongodb-atlas` for `document`). This separation means the same logical spec works across engines; switching from Postgres to Aurora or from DynamoDB to Cassandra doesn't change the datastore declaration — only the managed-services entry.

Recognized `form` values:

| Form | Examples (not prescriptive) |
|---|---|
| `relational` | Postgres, MySQL, RDS, Aurora, Cloud SQL, SQL Server |
| `document` | MongoDB, Firestore, Cosmos DB, DocumentDB |
| `key_value` | DynamoDB, Cassandra, ScyllaDB, Redis (when used as primary store, not cache) |
| `column_family` | HBase, Bigtable |
| `graph` | Neo4j, Neptune, TigerGraph |
| `search` | Elasticsearch, OpenSearch, Algolia, Typesense |
| `time_series` | InfluxDB, Timestream, Prometheus, TimescaleDB |

The `ownership` declaration applies to **all three resource types** in this section (datastores, storage_buckets, caches). A module cannot mix exclusive datastores with shared buckets — split into separate modules if ownership semantics differ by resource type.

---

### L2.A.5 — Interface

```yaml
interface:
  entry_points:
    - kind:          <interface_kind>
      # kind-specific fields:
      endpoint:      <string>
      method:        GET | POST | PUT | DELETE | PATCH | HEAD | OPTIONS
      event:         <event_name>
      schedule:      <cron_expression>
      # common fields:
      invokes:       <atom_id | flow_id | journey_id>
      request_type:  <type_id>
      response_type: <type_id>
      # security override (optional):
      security:
        authentication: required | optional | none
        auth_methods:   [<method>, ...]
        roles:          [<role_name>, ...]
```

Recognized interface kinds: `api`, `event_consumer`, `cli`, `scheduled`, `websocket`, `grpc`, `web_journey_entry`, `mobile_journey_entry`.

Kind-specific field requirements:

| Kind | Required fields |
|------|----------------|
| `api` | `endpoint`, `method` |
| `grpc` | `endpoint` |
| `event_consumer` | `event` |
| `scheduled` | `schedule` |
| `websocket` | `endpoint` |
| `cli` | (none beyond common) |
| `web_journey_entry` | `endpoint` |
| `mobile_journey_entry` | (none beyond common) |

`cli` entry points declare no implementation-specific fields (no command strings, no argument specs). Those bind at implementation time; the schema remains abstract.

`security` block is optional. When absent, the entry point inherits L1 `default_posture`. When present, overrides for this entry point only. Roles must exist in L1 `security.roles`. Entry points may restrict `auth_methods` from L1's list but not expand it.

`request_type` and `response_type` are optional. Reference L0.4 types.

---

### L2.A.6 — Access Permissions

```yaml
access_permissions:
  env_vars:         [<string>, ...]
  filesystem:       [<path>, ...]
  network:          [<domain>, ...]
  secrets:          [<string>, ...]
  external_schemas: [<schema_id>, ...]
```

Whitelist. Anything not listed is forbidden. All five fields mandatory; empty lists for unused categories.

`external_schemas` entries must resolve to keys in L0.7 `external_schemas`. A module that calls a third-party service must list the service's schema id here — free-form domains in `network` are not enough to establish the link.

---

### L2.A.7 — Dependency Whitelist

```yaml
dependency_whitelist:
  modules: [<module_id>, ...]
```

Explicit list of other modules this module may call. Cross-module atom calls to unlisted modules fail at stage 4 validation.

No acyclicity constraint — mutually dependent modules (e.g., saga participants) are permitted.

---

### L2.A.8 — Policies

```yaml
policies: [<policy_id>, ...]
```

List of policy IDs applied to this module's atoms. Policies defined in L2.B files.

---

### L2.A.9 — Changelog

```yaml
changelog:
  - version:     <string>
    date:        <YYYY-MM-DD>
    change_type: added | modified | deprecated | removed | fixed
    description: <string>
```

---

## L2.B — Policy Spec

Policies are targeted cross-cutting rules. L1 conventions apply universally; policies apply only to modules that opt in.

### Top-level structure

```yaml
policy:
  id:          <policy_id>
  name:        <string>
  description: <string>

  applies_when: <predicate_expression>

  mandatory_behavior:
    before:        <action_expression>
    after_success: <action_expression>
    after_failure: <action_expression>

  opt_out:
    allowed:                <boolean>
    requires_justification: <boolean>

  changelog: [...]
```

---

### L2.B.1 — Identity

```yaml
policy:
  id:          <policy_id>
  name:        <string>
  description: <string>
```

`id` must match `naming_ledger.policy_id`.

---

### L2.B.2 — Applies When

```yaml
applies_when: <predicate_expression>
```

Predicate over atom properties using pseudo-formal syntax: `atom.side_effects contains WRITES_DB`, `atom.id matches "atm.pay.refund_*"`, etc. Only atoms owned by modules that list this policy are evaluated.

Side-effect markers referenced in the predicate must exist in L0.6 (`side_effect_markers`).

---

### L2.B.3 — Mandatory Behavior

```yaml
mandatory_behavior:
  before:        <action_expression>
  after_success: <action_expression>
  after_failure: <action_expression>
```

All three fields optional — declare only hooks needed. Actions are pseudo-formal statements.

Error codes referenced in actions must exist in L0.3 (`errors`).

---

### L2.B.4 — Opt Out

```yaml
opt_out:
  allowed:                <boolean>
  requires_justification: <boolean>
```

If `allowed: false`, no atom can escape this policy. If `allowed: true` and `requires_justification: true`, atoms must provide a reason string when opting out.

---

### L2.B.5 — Changelog

Standard changelog.

---

## Validation Rules

### Module validation

1. `module.id` matches `naming_ledger.module_id`.
2. Every `owned_atoms` entry matches `naming_ledger.atom_id`.
3. Every `owned_artifacts` entry matches `naming_ledger.artifact_id`.
4. Every atom and artifact in the project appears in exactly one module's owned inventory.
5. Every `persistence_schema.datastores[].type` resolves to an existing key in L0.4 `types` **with `kind: entity`**. Enum types cannot be datastore entries.
5a. Every `persistence_schema.datastores[].form` is present and one of: `relational`, `document`, `key_value`, `column_family`, `graph`, `search`, `time_series`.
6. Every `interface.entry_points[].event` matches `naming_ledger.event_name`.
7. Every `interface.entry_points[].invokes` resolves to a real atom, flow, or journey.
8. Every `interface.entry_points[].request_type` and `response_type` resolves to an existing key in L0.4 `types`.
9. Every role in entry point `security.roles` exists in L1 `security.roles`.
10. Entry point `security.auth_methods` is a subset of L1 `default_posture.auth_methods`.
11. Every `dependency_whitelist.modules` entry resolves to a real module.
12. Every `policies` entry matches `naming_ledger.policy_id` and resolves to a real policy file.
13. If `persistence_schema.ownership == shared`, `shared_with` is non-empty and all entries resolve to real modules.
14. `tech_stack.language_version` and `tech_stack.runtime_version` match `^[\w.\-]+(\.x)?$` and are non-empty.
15. Every entry in `tech_stack.frameworks` and `tech_stack.mandatory_libraries` matches `^[a-z0-9_\-/.]+@[\w.\-]+(\.x)?$`.
16. Every `interface.entry_points[].method` (when present) is one of `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`.
17. Kind-specific required fields are present per this table:
    - `api` → `endpoint`, `method`
    - `grpc` → `endpoint`
    - `event_consumer` → `event`
    - `scheduled` → `schedule`
    - `websocket` → `endpoint`
    - `web_journey_entry` → `endpoint`
    - `cli`, `mobile_journey_entry` → no kind-specific required fields
18. Kind-irrelevant fields are absent per the same table (e.g., an `api` entry point must not declare `event` or `schedule`).
19. Every `access_permissions.external_schemas` entry resolves to an existing key in L0.7 `external_schemas`.
20. Every `scheduled` entry point's `schedule` is a syntactically valid cron expression (5- or 6-field form).
21. **Project-wide**: no two `api` entry points across all modules share the same `(endpoint, method)` pair. No two `grpc` entry points share `endpoint`. No two `websocket` or `web_journey_entry` entry points share `endpoint`.
22. `tech_stack.compute` (when present) is a non-empty string. No fixed enum.
23. `tech_stack.managed_services` (when present) is a list; each entry has non-empty `service` and `purpose` strings.
24. `tech_stack.source_root` (when present) is a non-empty string — a relative path from the project root where this module's implementation code lives. No fixed enum.
25. `tech_stack.schema_tool` (when present) is a non-empty string naming the tooling used for DECLARATIVE atoms targeting `database_schema` (e.g., `prisma`, `drizzle`, `raw-sql`, `sqlalchemy`, `alembic`). No fixed enum.
26. `tech_stack.iac_tool` (when present) is a non-empty string naming the tooling used for DECLARATIVE atoms targeting `infrastructure` (e.g., `terraform`, `pulumi`, `aws-cdk`, `cloudformation`). No fixed enum.

### Policy validation

1. `policy.id` matches `naming_ledger.policy_id`.
2. `applies_when` is a parseable predicate expression.
3. Error codes referenced in `mandatory_behavior` actions exist as keys in L0.3 `errors`.
4. Side-effect markers referenced in `applies_when` exist as keys in L0.6 `side_effect_markers`.
5. At least one module references this policy (orphan policies flagged as warnings).
