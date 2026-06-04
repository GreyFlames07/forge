# Forge Schema Reference

Forge has three central schema files and code-owned C3 annotations.

```text
forge/
  system.yaml
  containers.yaml
  entities.yaml
```

```text
@forge:component
@forge:type
@forge:persistence
@forge:operation
```

Central files own C1/C2 truth. Implementation files own C3 truth.

## `forge/system.yaml`

```yaml
schema: forge.system

system:
  id: string
  purpose: string
  description: string
  boundary: string
  security: string

  actors:
    - id: string
      kind: human | system
      description: string

  external_dependencies:
    - id: string
      kind: system | service | datastore | api
      description: string
      documentation_url?: string

  business_actions:
    - id: string
      actor: string
      intent: string
      outcomes:
        - string
      notes?: string
```

Rules:

- `business_actions` are business intent, not runtime flows.
- Actor references must resolve to `system.actors`.
- Use `snake_case` ids.

## `forge/containers.yaml`

```yaml
schema: forge.containers

containers:
  - id: string
    kind: server_side_web_application |
          client_side_web_application |
          client_side_desktop_application |
          mobile_app |
          server_side_console_application |
          serverless_function |
          database |
          blob_or_content_store |
          file_system |
          shell_script |
          external_container
    technology: string
    description: string
    source_root?: string
    responsibilities:
      - string
    security: string
    deployment:
      - environment: string
        platform: string
        node: string
        endpoint: string
        notes: string

container_flows:
  - id: string
    business_action: string
    description: string
    trigger:
      actor?: string
      container: string
      input: string
    steps:
      - id: number
        from: string
        to: string
        input: string
        output?: string
        logic:
          - string
        next?: number
        branches?:
          - condition: string
            next: number
            output: string
    outcomes:
      - string
```

Rules:

- Deployment has no `manifestations` wrapper.
- Every deployment entry includes `environment`, `platform`, `node`,
  `endpoint`, and `notes`.
- `source_root` lets embedded annotations infer their container.
- There is no `relationships` section; relationships are derived from flow
  `from`/`to` edges.
- A step has `next`, `branches`, or neither. It must not have both `next` and
  `branches`.
- Branch and next targets may point forward, backward, or to the same step.

## `forge/entities.yaml`

```yaml
schema: forge.entities

entities:
  - id: string
    category: entity | record | lifecycle_object
    description: string
    lifecycle?:
      states:
        - string
      transitions?:
        - from: string
          to: string
          condition: string
    canonical_type:
      container: string
      component: string
      ref: string
    logical_owner:
      container: string
      component: string
    persisted_in?:
      container: string
      component: string
    security?: string
```

Rules:

- `canonical_type.ref` points to a data shape declared with `@forge:type`.
- `logical_owner` owns business meaning and lifecycle rules.
- `persisted_in` identifies durable storage location.
- Lifecycle transitions must reference known states.

## Embedded C3 Annotations

Annotations use host-language comments with YAML-like content after the marker.
They should be written in the same code change as the implementation behavior
they describe.

### `@forge:component`

```yaml
@forge:component
id: string
container?: string
role: interface | logic | persistence | datastore | external_adapter | utility
parent_component?: string
description: string
interface?:
  kind: screen | router | worker | scheduler | event_boundary | cli | file_boundary | subsurface
  surface: string
  actor?: string
  external_dependency?: string
  container_flows:
    - string
  input?: string
  output?: string
  security?: string
data_shapes:
  - string
responsibilities:
  - string
security?: string
```

Rules:

- `container` is optional when the file is under a container `source_root`.
- `role: interface` requires `interface`.
- `interface.kind: subsurface` requires `parent_component`.
- Do not model decorative or layout-only children as components.

Examples:

```yaml
@forge:component
id: account_router
role: interface
description: Backend route group for account operations.
interface:
  kind: router
  surface: /account
  container_flows:
    - update_account
data_shapes:
  - update_account_request
  - update_account_response
responsibilities:
  - Accept account API requests.
  - Convert HTTP requests into account commands.
```

```yaml
@forge:component
id: account_summary_card
role: interface
parent_component: account_screen
description: Nested card that summarizes account state.
interface:
  kind: subsurface
  surface: account.summary-card
  container_flows:
    - update_account
data_shapes:
  - account_summary_state
responsibilities:
  - Display account summary values.
  - Surface validation warnings.
```

```yaml
@forge:component
id: account_service
role: logic
description: Applies account business rules.
data_shapes:
  - update_account_command
  - account_update_result
responsibilities:
  - Authorize account updates.
  - Apply account update rules.
```

```yaml
@forge:component
id: account_repository
role: persistence
description: Reads and writes account records.
data_shapes:
  - account_record
responsibilities:
  - Read account records.
  - Persist account updates.
```

```yaml
@forge:component
id: account_store
role: datastore
description: Datastore area for account records.
data_shapes:
  - account_record
responsibilities:
  - Store account records.
  - Support lookup by account id.
```

```yaml
@forge:component
id: identity_provider_adapter
role: external_adapter
description: Adapter for identity provider APIs.
data_shapes:
  - identity_profile_request
  - identity_profile_response
responsibilities:
  - Call identity provider APIs.
  - Normalize provider responses.
```

```yaml
@forge:component
id: account_response_mapper
role: utility
description: Shared mapper for account response payloads.
data_shapes:
  - account_record
  - account_response
responsibilities:
  - Convert account records into API responses.
```

### `@forge:type`

```yaml
@forge:type
id: string
type_kind: payload | state | persistent_state | ui_state | event | command | query | response | error
entity?: string
description?: string
shape:
  field_name: type
```

Shape syntax:

```yaml
shape:
  required_field: string
  optional_field?: string
  nested:
    child: integer
  inline_array:
    - child: string
  typed_array: "[ref[item_type]]"
  primitive_array: [string]
  dictionary: "{string: ref[item_type]}"
  typed_dictionary: "{ref[key_type]: ref[value_type]}"
```

Allowed primitives/conventions:

```text
string
integer
decimal
boolean
datetime
vector
enum[value_a, value_b]
ref[type_id]
[type]
{key_type: value_type}
@min, @max, @regex, @dimensions
```

Example:

```yaml
@forge:type
id: update_account_request
type_kind: command
shape:
  account_id: string
  display_name?: string
  notification_channels: [string]
  preferences: {string: string}
```

### `@forge:persistence`

```yaml
@forge:persistence
entity: string
storage_model: relational | document | key_value | vector | time_series | graph | blob | file_system
physical_store: string
table?: string
collection?: string
path?: string
migrations_path?: string
access_patterns:
  - string
lifecycle?:
  states:
    - string
  transitions:
    - from: string
      to: string
      condition: string
security: string
```

Example:

```yaml
@forge:persistence
entity: account
storage_model: relational
physical_store: primary_database
table: accounts
migrations_path: migrations
access_patterns:
  - read account by account_id
  - update account settings by account_id
security: Account records require authenticated access and audit logging.
```

### `@forge:operation`

```yaml
@forge:operation
id: string
input: string
returns: string
logic:
  - string
participates_in:
  - container_flow: string
    local_flow: string
    step: number
    passes?: string
    flow_logic?:
      - string
    next?: number
    branches?:
      - condition: string
        next: number
        passes: string
security?: string
```

Example:

```yaml
@forge:operation
id: update_account_handler
input: ref[update_account_request]
returns: ref[http_response]
logic:
  - Validate request shape.
  - Extract authenticated user context.
  - Build account update command.
  - Return an HTTP response.
participates_in:
  - container_flow: update_account
    local_flow: update_account_backend
    step: 1
    passes: ref[update_account_command]
    flow_logic:
      - Start the backend account update flow.
    next: 2
```

Rules:

- Operation annotations are the source of truth for C3 component flows.
- `input`, `returns`, and `logic` describe the operation's code contract.
- `participates_in` describes where the operation appears in one or more
  container/local flows.
- `passes` is the conceptual payload handed to the next local flow step.
- `flow_logic` is optional flow-specific context; it must not contradict the
  operation's core `logic`.
- `next` and `branches` live inside `participates_in` entries and follow the
  same step rules as container flows.
- If the operation's input, return type, or core logic differs, use a separate
  operation.

## Extracted Model

Forge generates this model from central schema plus code annotations.

```yaml
schema: forge.extracted_components

components:
  - id: string
    container: string
    role: string
    source: string
    parent_component?: string
    interface?: object
    data_shapes:
      - string
    responsibilities:
      - string

data_shapes:
  - id: string
    component: string
    container: string
    type_kind: string
    source: string
    entity?: string
    shape: object

operations:
  - id: string
    component: string
    container: string
    source: string
    input: string
    returns: string
    logic:
      - string
    participates_in:
      - container_flow: string
        local_flow: string
        step: number
        passes?: string
        flow_logic?: list
        next?: number
        branches?: list
```

## Validation Summary

- Schema ids match `forge.system`, `forge.containers`, or `forge.entities`.
- All ids are unique within their collection.
- All references resolve.
- Container `source_root` values are unique when present.
- Flow steps do not mix `next` and `branches`.
- Deployment entries include required fields.
- Component annotations resolve to a container.
- Interface components include valid interface metadata.
- Type refs in operation `input`, `returns`, and `passes` resolve to data
  shapes.
- Operation `participates_in` entries reference known container flows.
- Operation `participates_in` entries do not override operation `input`,
  `returns`, or core `logic`.
