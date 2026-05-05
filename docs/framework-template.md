# Framework Template

A blank schema for describing a system using the framework. Each section contains a node definition with placeholders. Replace anything inside `<…>` with your own values. Anything outside `<…>` is fixed framework vocabulary.

**Conventions:**
- IDs are hierarchical dot-paths: `<conception>.<system>.<domain>.<module>.<element>.<property_or_operation>`. Position encodes node type; labels are not repeated in the ID.
- Registries hang off their owning node with a single segment: `<conception>.<system>.types.<TypeName>`, `<conception>.actors.<ActorName>`, etc.
- A node's parent is encoded in its ID; do not add a `parent` field.
- Enum-valued fields reference `framework.enums.{Name}`. Pick one defined value; do not invent new ones inline.
- Domain-specific enumerations belong in the type registry as scalar types with `enum_values` constraints, never inline.
- `version` appears only on Module, composite Type, Contract, and Datastore.
- Built-in scalars (`String`, `Integer`, `Float`, `Boolean`, `Timestamp`, `UUID`, `Blob`) are referenced as `system.types.{Name}` and need not be redefined.
- Built-in errors (`NotFound`, `Unauthorized`, `Forbidden`, `Conflict`, `ValidationFailed`, `Unavailable`, `Timeout`) are referenced as `system.errors.{Name}` and need not be redefined.
- Optional fields may be omitted entirely. Empty arrays (`[]`) are explicit; omitted fields are absent.
- Multiple instances of the same node type within a section are separated by `---`.
- Policies cascade from a node to every descendant automatically. Lower nodes may add more specific policies; they accumulate.
- Node history is managed by version control. No changelog fields appear on nodes.

---

## 0. Framework Enums

Fixed vocabulary. Reference these values throughout the spec. Do not extend inline; add new values here only.

```yaml
framework:
  enums:
    Status:
      values: [draft, active, deprecated, retired]

    AuthMechanism:
      values: [none, jwt, api_key, oauth2, mtls, hmac, session]

    Permission:
      values: [read, write, delete, execute]

    Deployment:
      values: [cloud, on_prem, hybrid, edge]

    Packaging:
      values: [service, gateway, job, function, worker, library]

    Scaling:
      values: [none, vertical, horizontal, auto]

    ElementKind:
      values: [aggregate, entity, value_object, service, projection]

    OperationKind:
      values: [command, query, async_command, async_query, event_handler, subscription]

    RelationshipType:
      values: [depends_on, extends, contains, references, triggers]

    Multiplicity:
      values: [one_to_one, one_to_many, many_to_one, many_to_many]

    Embedding:
      values: [inline, reference, derived, external]

    Visibility:
      values: [public, internal, private]

    Protocol:
      values: [rest, grpc, queue, websocket, graphql, event_bus, cli]

    VersioningStrategy:
      values: [uri, header, query_param]

    StorageType:
      values: [relational, document, key_value, timeseries, cache, graph, search, column_family, object_store]

    DatastorePurpose:
      values: [primary, cache, projection, archive]

    SourceKind:
      values: [element_state, projection, derived, external]

    DatastoreRole:
      values: [read, write, both]

    EnvironmentKind:
      values: [development, staging, production, test]

    Consistency:
      values: [strong, eventual, bounded_staleness, session]

    Durability:
      values: [ephemeral, persistent, replicated]

    Classification:
      values: [public, internal, confidential, restricted]

    Persistence:
      values: [permanent, transient, ephemeral]

    RetentionPolicy:
      values: [delete, archive, anonymise]

    RuleKind:
      values: [sla, rate_limit, validation, invariant, workflow]

    Enforcement:
      values: [hard, soft, advisory]

    FailureAction:
      values: [abort, retry, skip, compensate, fallback]

    DeploymentStatus:
      values: [pending, active, rolled_back, failed]

    TestKind:
      values: [unit, integration, contract, e2e, performance]

    LogLevel:
      values: [debug, info, warn, error, fatal]

    RetryBackoff:
      values: [fixed, linear, exponential]

    AuditTrigger:
      values: [on_write, on_read, on_delete, on_error, always]

    IdempotencyStrategy:
      values: [key_dedup, natural_key, conditional_insert]

    RateLimitScope:
      values: [per_actor, per_ip, per_api_key, global]
```

---

## 1. Conception

```yaml
id: <conception>
type: conception
name: <ConceptionName>
description: <one-sentence description>
status: <framework.enums.Status>
owner: <team or individual>
intent: >
  <multi-line statement of what this conception aims to achieve
  and the constraints that define it>
systems:
  - <conception>.<system>
actors:
  - id: <conception>.actors.<actor>
    name: <ActorName>
    description: <who this actor represents>
    kind: <human | service | partner | internal_system>
    auth_mechanism: <framework.enums.AuthMechanism>
    default_permissions:
      - <framework.enums.Permission>
glossary:
  - id: <conception>.glossary.<term>
    term: <human-readable term>
    definition: >
      <precise definition as used in this conception>
    synonyms:
      - <term that should NOT be used>
    related_terms:
      - <conception>.glossary.<other_term>
    appears_in:
      - <node.id>
policies: []
```

## 2. System

```yaml
id: <conception>.<system>
type: system
name: <SystemName>
description: <one-sentence description of system purpose>
status: <framework.enums.Status>
owner: <team>
domains:
  - <conception>.<system>.<domain>
platform: <e.g. AWS, GCP, on-prem-k8s>
language: <primary language>
deployment: <framework.enums.Deployment>
policies:
  - <conception>.<system>.policies.<policy>
```

---

## 5. Domain

```yaml
id: <conception>.<system>.<domain>
type: domain
name: <DomainName>
description: <one-sentence description>
status: <framework.enums.Status>
owner: <sub-team>
responsibility: >
  <what this domain is responsible for and what it explicitly is not>
modules:
  - <conception>.<system>.<domain>.<module>
policies: []
```

---

## 6. Module

```yaml
id: <conception>.<system>.<domain>.<module>
type: module
name: <ModuleName>
description: <one-sentence description>
status: <framework.enums.Status>
owner: <team>
version: <semver>
packaging:
  kind: <framework.enums.Packaging>
  runtime: <e.g. node20, python3.12, jvm17>
  scaling: <framework.enums.Scaling>
external_dependencies:
  - <conception>.<system>.integrations.<integration>
elements:
  - <conception>.<system>.<domain>.<module>.<element>
policies: []
```

---

## 7. Element

```yaml
id: <conception>.<system>.<domain>.<module>.<element>
type: element
name: <ElementName>
description: <one-sentence description>
status: <framework.enums.Status>
owner: <team>
kind: <framework.enums.ElementKind>
properties:
  - <conception>.<system>.<domain>.<module>.<element>.<property>
operations:
  - <conception>.<system>.<domain>.<module>.<element>.<operation>
relationships:
  - target: <element.id>
    type: <framework.enums.RelationshipType>
    multiplicity: <framework.enums.Multiplicity>
policies: []
```

---

## 8. Property

```yaml
id: <conception>.<system>.<domain>.<module>.<element>.<property>
type: property
name: <property>
description: <one-sentence description>
status: <framework.enums.Status>
data_type: <type.id>
is_array: <true | false>
is_nullable: <true | false>
embedding: <framework.enums.Embedding>
visibility: <framework.enums.Visibility>
default: <default value or omit>
```

---

## 9. Operation

```yaml
id: <conception>.<system>.<domain>.<module>.<element>.<operation>
type: operation
name: <operation>
description: <one-sentence description of what this operation does>
status: <framework.enums.Status>
kind: <framework.enums.OperationKind>
inputs:
  - <type.id>
outputs:
  - <type.id>
raises:
  - <error.id>
visibility: <framework.enums.Visibility>
contract: <contract.id>
policies: []
```

---

## 10. Type Registry

### Scalar

Wraps a primitive with constraints. Referenced by properties and composite types.

```yaml
id: <conception>.<system>.types.<TypeName>
type: type
name: <TypeName>
description: <what this scalar represents>
status: <framework.enums.Status>
kind: scalar
base: <system.types.Primitive>
constraints:
  pattern: <regex>
  min_length: <integer>
  max_length: <integer>
  min: <number>
  max: <number>
  enum_values:
    - <allowed value>
examples:
  - <example value>
```

### Composite

Built from scalars and other composites. Used as operation inputs/outputs, contract I/O, and datastore schemas.

```yaml
id: <conception>.<system>.types.<TypeName>
type: type
name: <TypeName>
description: <what this composite represents>
status: <framework.enums.Status>
kind: composite
version: <semver>
properties:
  - name: <field>
    data_type: <type.id>
    is_array: <true | false>
    is_nullable: <true | false>
    embedding: <framework.enums.Embedding>
    default: <default value or omit>
examples:
  - <example record>
```

---

## 11. Error Registry

```yaml
id: <conception>.<system>.errors.<ErrorName>
type: error
name: <ErrorName>
description: <when this error is raised>
status: <framework.enums.Status>
code: <STABLE_UPPERCASE_CODE>
http_status: <integer>
fields:
  - name: <field>
    data_type: <type.id>
```

---

## 12. Policy Registry

Policies cascade to all descendant nodes. Multiple policies accumulate; lower nodes do not override ancestors.

### Security Policy

```yaml
id: <conception>.<system>.policies.<policy>
type: policy
name: <PolicyName>
description: <what this policy enforces>
status: <framework.enums.Status>
owner: <team>
kind: security
authentication:
  required: <true | false>
  mechanism: <framework.enums.AuthMechanism>
authorisation:
  roles:
    - <role name>
  permissions:
    - <framework.enums.Permission>
  rule: <expression describing access rule>
encryption:
  at_rest: <true | false>
  in_transit: <true | false>
  field_level: <true | false>
```

### Business Policy

```yaml
id: <conception>.<system>.policies.<policy>
type: policy
name: <PolicyName>
description: <what this policy enforces>
status: <framework.enums.Status>
owner: <team>
kind: business
rule_kind: <framework.enums.RuleKind>
rule: <expression describing the rule>
enforcement: <framework.enums.Enforcement>
error: <error.id>
sla:
  max_response_ms: <integer>
  availability_percent: <float>
  rate_limit: <integer>
```

### Data Policy

```yaml
id: <conception>.<system>.policies.<policy>
type: policy
name: <PolicyName>
description: <what this policy governs>
status: <framework.enums.Status>
owner: <team>
kind: data
classification: <framework.enums.Classification>
persistence: <framework.enums.Persistence>
retention:
  duration: <ISO 8601 duration, e.g. P30D, P1Y>
  policy: <framework.enums.RetentionPolicy>
consistency: <framework.enums.Consistency>
backup:
  required: <true | false>
  frequency: <ISO 8601 duration>
```

### Operational Policy

```yaml
id: <conception>.<system>.policies.<policy>
type: policy
name: <PolicyName>
description: <what this policy governs>
status: <framework.enums.Status>
owner: <team>
kind: operational
logging:
  level: <framework.enums.LogLevel>
  log_entry: <true | false>
  log_exit: <true | false>
  log_errors: <true | false>
retry:
  - error: <error.id>
    max_attempts: <integer>
    backoff: <framework.enums.RetryBackoff>
    delay_ms: <integer>
audit:
  trigger: <framework.enums.AuditTrigger>
  fields:
    - <field name>
  sink: <datastore.id>
idempotency:
  key_field: <field name>
  ttl: <ISO 8601 duration>
  strategy: <framework.enums.IdempotencyStrategy>
rate_limit:
  requests_per_minute: <integer>
  burst: <integer>
  scope: <framework.enums.RateLimitScope>
```

---

## 13. Contract Registry

The binding between a producer module and its consumers. Versioned as a unit.

```yaml
id: <conception>.<system>.contracts.<contract>
type: contract
name: <ContractName>
description: <one-sentence description>
status: <framework.enums.Status>
owner: <team>
version: <semver>
protocol: <framework.enums.Protocol>
inputs:
  - <type.id>
outputs:
  - <type.id>
errors:
  - <error.id>
producer: <module.id>
consumers:
  - <module.id>
versioning:
  current: <semver>
  deprecated:
    - <semver>
  strategy: <framework.enums.VersioningStrategy>
policies: []
```

---

## 14. Integration Registry

An external dependency that implements a contract defined in this system.

```yaml
id: <conception>.<system>.integrations.<integration>
type: integration
name: <IntegrationName>
description: <one-sentence description of what this integration provides>
status: <framework.enums.Status>
provider: <third-party name, e.g. Stripe, Twilio, Auth0>
contract: <contract.id>
auth_mechanism: <framework.enums.AuthMechanism>
base_url: <url>
docs: <url>
```

---

## 15. Interaction Registry

A single directed call between two operations. The dependency graph is recoverable from this registry.

```yaml
id: <conception>.<system>.interactions.<interaction>
type: interaction
name: <InteractionName>
description: <one-sentence description>
status: <framework.enums.Status>
caller: <operation.id>
callee: <operation.id>
trigger: <technical cause of the call>
policies:
  - <policy.id>
```

---

## 16. Flow Registry

Orchestrates interactions into a named sequence. Supports parallel execution and conditional steps.

```yaml
id: <conception>.<system>.flows.<flow>
type: flow
name: <FlowName>
description: <one-sentence description>
status: <framework.enums.Status>
owner: <team>
trigger: <business event that initiates the flow>
steps:
  - order: <integer>
    interaction: <interaction.id>
    depends_on:
      - <interaction.id>
    parallel_group: <string>      # steps sharing a group id run concurrently
    condition: <expression>       # step executes only if expression evaluates to true
    on_failure: <framework.enums.FailureAction>
    compensation: <interaction.id>  # interaction that undoes this step; required when on_failure: compensate
postconditions:
  - <policy.id>
policies: []
```

**Parallel execution**: assign the same `parallel_group` value to steps that may run concurrently. Steps without a `parallel_group` run sequentially according to `order` and `depends_on`.

**Conditional execution**: `condition` is an expression over prior step outputs, e.g. `steps.verify.output.approved == true`. A step whose condition evaluates to false is skipped without failure.


## 18. Test Registry

Tests are first-class spec nodes built from the operations, flows, and elements defined in the spec.

```yaml
id: <conception>.<system>.tests.<test>
type: test
name: <TestName>
description: <one-sentence description of what this test verifies>
status: <framework.enums.Status>
kind: <framework.enums.TestKind>
target: <operation.id | flow.id | element.id>
inputs:
  - <type.id>
expected_output: <type.id>
expected_error: <error.id>
preconditions:
  - <policy.id>
postconditions:
  - <policy.id>
```

---

## 19. Datastore Registry

```yaml
id: <conception>.<system>.datastores.<datastore>
type: datastore
name: <DatastoreName>
description: <one-sentence description of what is stored here>
status: <framework.enums.Status>
owner: <team>
version: <semver>
kind: <framework.enums.StorageType>
engine: <specific technology, e.g. postgres, redis, clickhouse, s3>
purpose: <framework.enums.DatastorePurpose>
consumers:
  - <module.id>
schemas:
  - type: <type.id | element.id>
    source:
      kind: <framework.enums.SourceKind>
      ref: <id of source — element, contract, type, datastore, or operation>
    storage_name: <table, collection, key prefix, bucket path, or index>
    role: <framework.enums.DatastoreRole>
schema_version: <semver>
consistency: <framework.enums.Consistency>
durability: <framework.enums.Durability>
policies:
  - <policy.id>
```

---

## 20. Environment Registry

```yaml
id: <conception>.<system>.environments.<environment>
type: environment
name: <EnvironmentName>
description: <one-sentence description>
status: <framework.enums.Status>
kind: <framework.enums.EnvironmentKind>
region: <region identifier>
overlays:
  - target: <node.id>
    field: <dotted path to field on target node>
    value: <override value>
datastores:
  - datastore: <datastore.id>
    connection: <connection string or secrets reference>
    instance_class: <hardware class identifier>
features:
  - name: <feature flag name>
    enabled: <true | false>
```

---

## 21. Deployment Registry

Optional. Records what was deployed where and when.

```yaml
id: <conception>.<system>.deployments.<deployment>
type: deployment
name: <DeploymentName>
description: <one-sentence description>
status: <framework.enums.DeploymentStatus>
module: <module.id>
environment: <environment.id>
version: <semver>
deployed_at: <ISO 8601 timestamp>
deployed_by: <identifier>
artifact: <image tag, package URL, or commit SHA>
rollback_target: <deployment.id>
```
