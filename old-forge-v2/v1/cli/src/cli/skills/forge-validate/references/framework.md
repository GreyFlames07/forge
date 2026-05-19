# Forge Framework Reference

Combined reference for the Forge spec system. Covers directory layout, ID resolution, all node schemas, framework enums, and validation rules.

---

## Directory Layout

```
<project-root>/
├── spec/
│   ├── conception.yaml                         # singleton; actors and glossary inline
│   └── <system>/
│       ├── system.yaml
│       ├── types/<TypeName>.yaml
│       ├── errors/<ErrorName>.yaml
│       ├── policies/<policy>.yaml
│       ├── contracts/<contract>.yaml
│       ├── integrations/<integration>.yaml
│       ├── interactions/<interaction>.yaml
│       ├── flows/<flow>.yaml
│       ├── implementation/
│       │   ├── datastores.yaml                 # multi-doc, separated by ---
│       │   ├── tests.yaml
│       │   ├── environments.yaml
│       │   └── deployments.yaml                # optional
│       ├── workbench/                          # forge process artifacts
│       │   ├── discovery.md
│       │   ├── review.md
│       │   ├── build-plan.md
│       │   └── validation.md
│       └── <domain>/
│           ├── domain.yaml
│           └── <module>/
│               ├── module.yaml
│               └── <element>.yaml              # properties + operations inline
└── src/
```

---

## ID Resolution

The CLI derives node IDs from file paths:

1. Read `conception.yaml` for the conception name.
2. Strip `spec/` prefix.
3. Strip role suffixes (`/system.yaml`, `/domain.yaml`, `/module.yaml`).
4. Strip `implementation/` segment from flat file paths.
5. Replace `/` with `.`, drop `.yaml`.
6. Prepend the conception name.

```
spec/shortener/links/link_manager/short_link.yaml
→ linkhub.shortener.links.link_manager.short_link

spec/shortener/types/ShortCode.yaml
→ linkhub.shortener.types.ShortCode
```

**Every node's `id` field must match its path-derived ID.**

---

## Framework Enums

```yaml
framework:
  enums:
    Status:           [draft, active, deprecated, retired]
    AuthMechanism:    [none, jwt, api_key, oauth2, mtls, hmac, session]
    Permission:       [read, write, delete, execute]
    Deployment:       [cloud, on_prem, hybrid, edge]
    Packaging:        [service, gateway, job, function, worker, library]
    Scaling:          [none, vertical, horizontal, auto]
    ElementKind:      [aggregate, entity, value_object, service, projection]
    OperationKind:    [command, query, async_command, async_query, event_handler, subscription]
    RelationshipType: [depends_on, extends, contains, references, triggers]
    Multiplicity:     [one_to_one, one_to_many, many_to_one, many_to_many]
    Embedding:        [inline, reference, derived, external]
    Visibility:       [public, internal, private]
    Protocol:         [rest, grpc, queue, websocket, graphql, event_bus, cli]
    VersioningStrategy: [uri, header, query_param]
    StorageType:      [relational, document, key_value, timeseries, cache, graph, search, column_family, object_store]
    DatastorePurpose: [primary, cache, projection, archive]
    SourceKind:       [element_state, projection, derived, external]
    DatastoreRole:    [read, write, both]
    EnvironmentKind:  [development, staging, production, test]
    Consistency:      [strong, eventual, bounded_staleness, session]
    Durability:       [ephemeral, persistent, replicated]
    Classification:   [public, internal, confidential, restricted]
    Persistence:      [permanent, transient, ephemeral]
    RetentionPolicy:  [delete, archive, anonymise]
    RuleKind:         [sla, rate_limit, validation, invariant, workflow]
    Enforcement:      [hard, soft, advisory]
    FailureAction:    [abort, retry, skip, compensate, fallback]
    DeploymentStatus: [pending, active, rolled_back, failed]
    TestKind:         [unit, integration, contract, e2e, performance]
    LogLevel:         [debug, info, warn, error, fatal]
    RetryBackoff:     [fixed, linear, exponential]
    AuditTrigger:     [on_write, on_read, on_delete, on_error, always]
    IdempotencyStrategy: [key_dedup, natural_key, conditional_insert]
    RateLimitScope:   [per_actor, per_ip, per_api_key, global]
```

---

## Node Schemas

### Conception (`conception.yaml`)

```yaml
id: <conception>
type: conception
name: <ConceptionName>
description: <one-sentence>
status: <Status>
owner: <team or individual>
intent: >
  <multi-line statement of purpose and constraints>
systems:
  - <conception>.<system>
actors:
  - id: <conception>.actors.<actor>
    name: <ActorName>
    description: <who this actor represents>
    kind: <human | service | partner | internal_system>
    auth_mechanism: <AuthMechanism>
    default_permissions:
      - <Permission>
glossary:
  - id: <conception>.glossary.<term>
    term: <human-readable term>
    definition: >
      <precise definition>
    synonyms: [<term not to use>]
    related_terms: [<conception>.glossary.<other>]
    appears_in: [<node.id>]
policies: []
```

### System (`<system>/system.yaml`)

```yaml
id: <conception>.<system>
type: system
name: <SystemName>
description: <one-sentence>
status: <Status>
owner: <team>
domains:
  - <conception>.<system>.<domain>
platform: <e.g. AWS, GCP, on-prem-k8s>
language: <primary language>
deployment: <Deployment>
policies:
  - <policy.id>
```

### Domain (`<system>/<domain>/domain.yaml`)

```yaml
id: <conception>.<system>.<domain>
type: domain
name: <DomainName>
description: <one-sentence>
status: <Status>
owner: <sub-team>
responsibility: >
  <what this domain owns and explicitly does not own>
modules:
  - <conception>.<system>.<domain>.<module>
policies: []
```

### Module (`<system>/<domain>/<module>/module.yaml`)

```yaml
id: <conception>.<system>.<domain>.<module>
type: module
name: <ModuleName>
description: <one-sentence>
status: <Status>
owner: <team>
version: <semver>
packaging:
  kind: <Packaging>
  runtime: <e.g. node20, python3.12, jvm17>
  scaling: <Scaling>
external_dependencies:
  - <conception>.<system>.integrations.<integration>
elements:
  - <conception>.<system>.<domain>.<module>.<element>
policies: []
```

### Element (`<system>/<domain>/<module>/<element>.yaml`)

```yaml
id: <conception>.<system>.<domain>.<module>.<element>
type: element
name: <ElementName>
description: <one-sentence>
status: <Status>
owner: <team>
kind: <ElementKind>
properties:
  - id: <conception>.<system>.<domain>.<module>.<element>.<property>
    type: property
    name: <property>
    description: <one-sentence>
    status: <Status>
    data_type: <type.id>
    is_array: <true | false>
    is_nullable: <true | false>
    embedding: <Embedding>
    visibility: <Visibility>
    default: <value or omit>
operations:
  - id: <conception>.<system>.<domain>.<module>.<element>.<operation>
    type: operation
    name: <operation>
    description: <one-sentence>
    status: <Status>
    kind: <OperationKind>
    inputs: [<type.id>]
    outputs: [<type.id>]
    raises: [<error.id>]
    visibility: <Visibility>
    contract: <contract.id>
    policies: []
    steps:                            # required for command/async_command/event_handler with non-trivial logic
      - order: <integer>
        description: <what happens in this step>
        calls: <operation.id or datastore.id>  # omit if no cross-boundary call
        raises: [<error.id>]                   # errors surfaced at this step
        condition: <expression>                # omit if unconditional
relationships:
  - target: <element.id>
    type: <RelationshipType>
    multiplicity: <Multiplicity>
policies: []
```

### Type — Scalar (`<system>/types/<TypeName>.yaml`)

```yaml
id: <conception>.<system>.types.<TypeName>
type: type
name: <TypeName>
description: <what this scalar represents>
status: <Status>
kind: scalar
base: <system.types.Primitive>   # String, Integer, Float, Boolean, Timestamp, UUID, Blob
constraints:
  pattern: <regex>
  min_length: <integer>
  max_length: <integer>
  min: <number>
  max: <number>
  enum_values: [<allowed value>]
examples: [<example value>]
```

### Type — Composite (`<system>/types/<TypeName>.yaml`)

```yaml
id: <conception>.<system>.types.<TypeName>
type: type
name: <TypeName>
description: <what this composite represents>
status: <Status>
kind: composite
version: <semver>
properties:
  - name: <field>
    data_type: <type.id>
    is_array: <true | false>
    is_nullable: <true | false>
    embedding: <Embedding>
    default: <value or omit>
examples: [<example record>]
```

### Error (`<system>/errors/<ErrorName>.yaml`)

```yaml
id: <conception>.<system>.errors.<ErrorName>
type: error
name: <ErrorName>
description: <when this error is raised>
status: <Status>
code: <STABLE_UPPERCASE_CODE>
http_status: <integer>
fields:
  - name: <field>
    data_type: <type.id>
```

Built-in errors (reference as `system.errors.{Name}`, no redefinition needed):
`NotFound`, `Unauthorized`, `Forbidden`, `Conflict`, `ValidationFailed`, `Unavailable`, `Timeout`

### Policy — Security (`<system>/policies/<policy>.yaml`)

```yaml
id: <conception>.<system>.policies.<policy>
type: policy
name: <PolicyName>
description: <what this enforces>
status: <Status>
owner: <team>
kind: security
authentication:
  required: <true | false>
  mechanism: <AuthMechanism>
authorisation:
  roles: [<role name>]
  permissions: [<Permission>]
  rule: <expression>
encryption:
  at_rest: <true | false>
  in_transit: <true | false>
  field_level: <true | false>
```

### Policy — Business

```yaml
kind: business
rule_kind: <RuleKind>
rule: <expression>
enforcement: <Enforcement>
error: <error.id>
sla:
  max_response_ms: <integer>
  availability_percent: <float>
  rate_limit: <integer>
```

### Policy — Data

```yaml
kind: data
classification: <Classification>
persistence: <Persistence>
retention:
  duration: <ISO 8601, e.g. P30D>
  policy: <RetentionPolicy>
consistency: <Consistency>
backup:
  required: <true | false>
  frequency: <ISO 8601>
```

### Policy — Operational

```yaml
kind: operational
logging:
  level: <LogLevel>
  log_entry: <true | false>
  log_exit: <true | false>
  log_errors: <true | false>
retry:
  - error: <error.id>
    max_attempts: <integer>
    backoff: <RetryBackoff>
    delay_ms: <integer>
audit:
  trigger: <AuditTrigger>
  fields: [<field name>]
  sink: <datastore.id>
idempotency:
  key_field: <field name>
  ttl: <ISO 8601>
  strategy: <IdempotencyStrategy>
rate_limit:
  requests_per_minute: <integer>
  burst: <integer>
  scope: <RateLimitScope>
```

### Contract (`<system>/contracts/<contract>.yaml`)

```yaml
id: <conception>.<system>.contracts.<contract>
type: contract
name: <ContractName>
description: <one-sentence>
status: <Status>
owner: <team>
version: <semver>
protocol: <Protocol>
inputs: [<type.id>]
outputs: [<type.id>]
errors: [<error.id>]
producer: <module.id>
consumers: [<module.id>]
versioning:
  current: <semver>
  deprecated: [<semver>]
  strategy: <VersioningStrategy>
policies: []
```

### Integration (`<system>/integrations/<integration>.yaml`)

```yaml
id: <conception>.<system>.integrations.<integration>
type: integration
name: <IntegrationName>
description: <one-sentence>
status: <Status>
provider: <third-party name>
contract: <contract.id>
auth_mechanism: <AuthMechanism>
base_url: <url>
docs: <url>
```

### Interaction (`<system>/interactions/<interaction>.yaml`)

```yaml
id: <conception>.<system>.interactions.<interaction>
type: interaction
name: <InteractionName>
description: <one-sentence>
status: <Status>
caller: <operation.id>
callee: <operation.id>
trigger: <technical cause>
policies: [<policy.id>]
```

### Flow (`<system>/flows/<flow>.yaml`)

```yaml
id: <conception>.<system>.flows.<flow>
type: flow
name: <FlowName>
description: <one-sentence>
status: <Status>
owner: <team>
trigger: <business event>
steps:
  - order: <integer>
    interaction: <interaction.id>
    depends_on: [<interaction.id>]
    parallel_group: <string>      # same value = concurrent execution
    condition: <expression>       # step skipped if false
    on_failure: <FailureAction>
    compensation: <interaction.id>
postconditions: [<policy.id>]
policies: []
```

### Datastore (`<system>/implementation/datastores.yaml`, multi-doc)

```yaml
id: <conception>.<system>.datastores.<datastore>
type: datastore
name: <DatastoreName>
description: <one-sentence>
status: <Status>
owner: <team>
version: <semver>
kind: <StorageType>
engine: <e.g. postgres, redis, clickhouse, s3>
purpose: <DatastorePurpose>
consumers: [<module.id>]
schemas:
  - type: <type.id | element.id>
    source:
      kind: <SourceKind>
      ref: <element, contract, type, datastore, or operation id>
    storage_name: <table / collection / key prefix / bucket path / index>
    role: <DatastoreRole>
schema_version: <semver>
consistency: <Consistency>
durability: <Durability>
policies: [<policy.id>]
```

### Environment (`<system>/implementation/environments.yaml`, multi-doc)

```yaml
id: <conception>.<system>.environments.<environment>
type: environment
name: <EnvironmentName>
description: <one-sentence>
status: <Status>
kind: <EnvironmentKind>
region: <region identifier>
overlays:
  - target: <node.id>
    field: <dotted path to field>
    value: <override value>
datastores:
  - datastore: <datastore.id>
    connection: <connection string or secrets reference>
    instance_class: <hardware class identifier>
features:
  - name: <feature flag name>
    enabled: <true | false>
```

### Test (`<system>/implementation/tests.yaml`, multi-doc)

```yaml
id: <conception>.<system>.tests.<test>
type: test
name: <TestName>
description: <one-sentence>
status: <Status>
kind: <TestKind>
target: <operation.id | flow.id | element.id>
inputs: [<type.id>]
expected_output: <type.id>
expected_error: <error.id>
preconditions: [<policy.id>]
postconditions: [<policy.id>]
```

### Deployment (`<system>/implementation/deployments.yaml`, multi-doc, optional)

```yaml
id: <conception>.<system>.deployments.<deployment>
type: deployment
name: <DeploymentName>
description: <one-sentence>
status: <DeploymentStatus>
module: <module.id>
environment: <environment.id>
version: <semver>
deployed_at: <ISO 8601 timestamp>
deployed_by: <identifier>
artifact: <image tag, package URL, or commit SHA>
rollback_target: <deployment.id>
```

---

## CLI Reference

```bash
forge init                              # initialise spec directory
forge list                              # list all nodes grouped by kind
forge list --kind element --ids-only    # enumerate element IDs for scripting
forge context <element-id>             # full context bundle for an element
forge context <element-id> --format markdown
forge inspect <id>                      # lightweight metadata probe
forge find <query> [--kind <kind>]     # substring search across IDs + descriptions
forge validate                          # structural lint; exits 0 if clean
forge graph                             # visualise the dependency graph
```

`forge context` walks the dependency graph from an element and emits: element (with inline properties and operations), parent module/domain/system, referenced contracts, types (transitive), errors, interactions, cascaded policies, and datastores. This is the primary tool for subagents.

---

## Key Rules

- Every `id` field must match its path-derived ID.
- Policies cascade from parent to all descendants — they accumulate, never override.
- `version` appears only on Module, composite Type, Contract, and Datastore.
- Built-in scalars (`String`, `Integer`, `Float`, `Boolean`, `Timestamp`, `UUID`, `Blob`) are referenced as `system.types.{Name}` — no redefinition.
- Registry dirs (`types/`, `errors/`, `policies/`, `contracts/`, `integrations/`, `interactions/`, `flows/`) exist only directly under a system directory.
- `implementation/` exists only directly under a system directory and contains only `datastores.yaml`, `tests.yaml`, `environments.yaml`, `deployments.yaml`.
- Element files contain only inline properties and operations.
- `workbench/` exists only directly under a system directory and contains only forge process artifacts.
- Operation `steps` are required for `command`, `async_command`, and `event_handler` operations with non-trivial logic (any operation that calls another operation, writes to a datastore, or branches). Simple `query` and `subscription` operations may omit steps.
