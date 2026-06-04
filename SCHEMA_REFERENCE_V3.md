# Forge V2 Schema Reference

## Authoring Discipline

Forge schema artifacts should be minimal, explicit, and verifiable:

- State assumptions instead of hiding uncertainty in invented structure.
- Add only fields, artifacts, and flows that serve the current architectural or build goal.
- Do not add speculative flexibility, optionality, or future-facing artifacts.
- Keep one-off payloads inline until reuse, persistence, or system significance justifies promotion.
- Touch the narrowest schema scope needed; do not refactor unrelated artifacts.
- Define review or validation criteria for every non-trivial schema change.

## System

Defines the highest-level truth about the system: what it is, why it exists, what is inside its boundary, who interacts with it, and which external systems it depends on.

```yaml
schema: forge.v2.system

system:
  id: string
  purpose: string
  description: string
  boundary: string
  security: string
  actors:
    - id: string
      description: string
      kind: human | system
  external_dependencies:
    - id: string
      description: string
      kind: system | service | datastore | api
      documentation_url: string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.system`.

`system.id`
- Canonical identifier for the system.
- This is the system name in machine-readable form.
- It should be stable and concise.

`system.purpose`
- Short statement of why the system exists.
- This should explain the core reason for the system, not its implementation.

`system.description`
- Plain-language description of the system.
- This should give a fuller explanation than `purpose`.

`system.boundary`
- Plain-language description of what is inside the system boundary.
- This should clarify what the system is responsible for.

`system.security`
- Plain-language description of the system-wide security posture and non-negotiable security rules.
- Use this for security expectations that apply across the whole system.

`system.actors`
- External humans or systems that directly interact with the system.
- This list should only include actors that matter at the system context level.

`system.actors[].id`
- Canonical identifier for the actor.
- This is also the actor name.

`system.actors[].description`
- Plain-language description of how the actor relates to the system.

`system.actors[].kind`
- The actor type.
- Allowed values: `human`, `system`.

`system.external_dependencies`
- External systems the system depends on.
- This should only include dependencies that matter at the system context level.

`system.external_dependencies[].id`
- Canonical identifier for the dependency.
- This is also the dependency name.

`system.external_dependencies[].description`
- Plain-language description of what the dependency is and why it matters to the system.

`system.external_dependencies[].kind`
- The dependency type.
- Allowed values: `system`, `service`, `datastore`, `api`.

`system.external_dependencies[].documentation_url`
- URL for the dependency's documentation.
- This should point to the most useful integration or product documentation when available.

### Example

```yaml
schema: forge.v2.system

system:
  id: clothes_marketplace
  purpose: Let customers browse clothing, place orders, and track purchases online.
  description: >
    Clothes Marketplace is an ecommerce system that allows customers to discover
    products, purchase them, and receive order updates, while allowing internal
    staff to manage catalog and order operations.
  boundary: >
    The system includes the customer-facing shopping experience, the internal
    application services that manage catalog and ordering workflows, and the
    persistence needed to support those workflows. External payment and delivery
    providers are outside the system boundary.
  security: >
    All customer-facing traffic must use HTTPS, all user actions must be
    attributable to an authenticated actor, and payment method details must
    never be stored directly by the system.
  actors:
    - id: customer
      description: Browses products, places orders, and tracks purchases.
      kind: human
    - id: operations_staff
      description: Manages catalog changes and reviews order activity.
      kind: human
  external_dependencies:
    - id: stripe
      description: External payment processor used to authorize and capture payments.
      kind: api
      documentation_url: https://docs.stripe.com
    - id: sendgrid
      description: External email delivery service used for transactional notifications.
      kind: service
      documentation_url: https://www.twilio.com/docs/sendgrid
```

## High-Level Flow

Defines what happens from a business or system point of view without introducing runtime units, contracts, or implementation detail.

```yaml
schema: forge.v2.high_level_flow

high_level_flow:
  id: string
  description: string
  trigger: string
  steps:
    - id: number
      description: string
      next: number
      branches:
        - condition: string
          next: number
  outcomes:
    - string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.high_level_flow`.

`high_level_flow.id`
- Canonical identifier for the flow.
- Multi-word ids should use `snake_case`.

`high_level_flow.description`
- Plain-language description of the flow.
- This should explain the business meaning of the flow, not implementation details.

`high_level_flow.trigger`
- Plain-language description of what starts the flow.

`high_level_flow.steps`
- Ordered business/system steps in the flow.
- These steps should describe what happens at a business level only.

`high_level_flow.steps[].id`
- Numeric identifier for the step.
- Step ids should be unique within the flow and should reflect ordering.

`high_level_flow.steps[].description`
- Plain-language description of what happens at that step.

`high_level_flow.steps[].next`
- Numeric id of the normal next step.
- This is used for a standard progression through the flow.
- A step may define `next` or `branches`, but never both.
- Terminal steps should omit this field.

`high_level_flow.steps[].branches`
- Optional list of decision branches from the current step.
- Use this when the step represents a business decision point.
- A step may define `branches` or `next`, but never both.

`high_level_flow.steps[].branches[].condition`
- Plain-language description of the condition that causes the branch.

`high_level_flow.steps[].branches[].next`
- Numeric id of the step that follows when the condition is met.

`high_level_flow.outcomes`
- Canonical business outcomes produced by the flow.
- These should describe the end result from a business or system point of view.

Additional rule:
- A step with `next` is a linear step.
- A step with `branches` is a decision step.
- A step with neither is a terminal step.
- A step with both is invalid.
- `next` and branch targets may point to earlier steps when the flow intentionally loops.

### Example

```yaml
schema: forge.v2.high_level_flow

high_level_flow:
  id: place_order
  description: >
    A customer selects products, submits an order, and receives confirmation
    that the order has been accepted by the system.
  trigger: Customer chooses to buy the items currently in their cart.
  steps:
    - id: 1
      description: Customer reviews cart and submits the order.
      next: 2
    - id: 2
      description: System checks whether the order can proceed.
      branches:
        - condition: Order details are valid and payment can be attempted.
          next: 3
        - condition: Order details are invalid or cannot proceed.
          next: 5
    - id: 3
      description: System attempts to complete the purchase.
      branches:
        - condition: Purchase succeeds.
          next: 4
        - condition: Purchase fails.
          next: 5
    - id: 4
      description: System confirms the order to the customer.
    - id: 5
      description: System informs the customer that the order could not be completed.
  outcomes:
    - Order is accepted and confirmed.
    - Order is rejected and the customer is informed.
```

## Early State

Defines the important business entities, records, and lifecycle objects at a lightweight level before exact state modeling begins.

```yaml
schema: forge.v2.early_state

early_state:
  - id: string
    description: string
    category: entity | record | lifecycleObject
    why_it_matters: string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.early_state`.

`early_state`
- List of important business state objects that matter at the framework level.
- This stage should stay lightweight and should not become a full type or data model.

`early_state[].id`
- Canonical identifier for the state object.
- Multi-word ids should use `snake_case`.

`early_state[].description`
- Plain-language description of what the state object is.
- If the object has a meaningful lifecycle, it can be described here.

`early_state[].category`
- The kind of state object being described.
- Allowed values:
  - `entity`: a meaningful business thing with identity across time
  - `record`: an important stored business object
  - `lifecycleObject`: an object whose state progression is important to the system

`early_state[].why_it_matters`
- Plain-language explanation of why this object matters and why it should be represented explicitly in the framework.

### Example

```yaml
schema: forge.v2.early_state

early_state:
  - id: order
    description: >
      The order represents a customer's intent to purchase one or more products.
      It begins when the customer submits the purchase and progresses through
      confirmation, payment, fulfillment, and completion or failure.
    category: lifecycleObject
    why_it_matters: >
      The order is the core business object that ties together purchasing,
      payment, fulfillment, and customer communication.
  - id: product
    description: >
      The product represents an item that can be listed, viewed, and purchased
      through the platform.
    category: entity
    why_it_matters: >
      Products are central to browsing, pricing, and ordering behavior across
      the system.
  - id: payment_attempt
    description: >
      The payment attempt records a single attempt to charge or authorize payment
      for an order.
    category: record
    why_it_matters: >
      Payment attempts are important for understanding order progress and failure
      conditions even before precise state modeling is introduced.
```

## Runtime

Defines the C4 containers that make up the runtime architecture and the relationships between them.

```yaml
schema: forge.v2.runtime

runtime:
  containers:
    - id: string
      description: string
      kind: enum[
        server_side_web_application,
        client_side_web_application,
        client_side_desktop_application,
        mobile_app,
        server_side_console_application,
        serverless_function,
        database,
        blob_or_content_store,
        file_system,
        shell_script,
        external_container
      ]
      technology: string
      responsibilities:
        - string
      security: string
  relationships:
    - from: string
      to: string
      description: string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.runtime`.

`runtime`
- Defines the runtime architecture in C4 container terms.
- A container is an application or a data store that must exist for the system to work.
- Deployment is a separate concern and is not defined here.

`runtime.containers`
- List of C4 containers in the system.
- These are runtime boundaries around executing code or stored data.

`runtime.containers[].id`
- Canonical identifier for the container.
- Multi-word ids should use `snake_case`.

`runtime.containers[].description`
- Plain-language description of the container and its role in the system.

`runtime.containers[].kind`
- The C4-aligned container type.
- Allowed values:
  - `server_side_web_application`
  - `client_side_web_application`
  - `client_side_desktop_application`
  - `mobile_app`
  - `server_side_console_application`
  - `serverless_function`
  - `database`
  - `blob_or_content_store`
  - `file_system`
  - `shell_script`
  - `external_container`

`runtime.containers[].technology`
- Primary technology, runtime, or platform used by the container.

`runtime.containers[].responsibilities`
- List of the main responsibilities owned by the container.
- These should describe what the container is responsible for in the system.

`runtime.containers[].security`
- Plain-language description of the container-specific security obligations.
- Use this for authentication, authorization, secrets handling, logging restrictions, encryption expectations, or access restrictions specific to the container.

`runtime.relationships`
- List of runtime relationships between containers.
- These define how containers connect to, depend on, or interact with one another.

`runtime.relationships[].from`
- The id of the source container.

`runtime.relationships[].to`
- The id of the target container.

`runtime.relationships[].description`
- Plain-language description of the relationship.
- This can include protocol, communication style, or interaction detail where useful.

### Example

```yaml
schema: forge.v2.runtime

runtime:
  containers:
    - id: storefront_web
      description: Customer-facing web application for browsing products and placing orders.
      kind: client_side_web_application
      technology: React
      responsibilities:
        - Render the shopping experience for customers.
        - Collect cart and checkout input.
        - Send order and product requests to backend services.
      security: >
        Must only communicate with backend services over HTTPS and must never
        store raw payment credentials in browser-accessible storage.
    - id: ordering_api
      description: Backend application that manages ordering workflows and coordinates payment and persistence.
      kind: server_side_web_application
      technology: FastAPI
      responsibilities:
        - Validate and accept order requests.
        - Persist order data.
        - Coordinate payment processing.
        - Return order outcomes to the storefront.
      security: >
        Must require authenticated requests where applicable, enforce
        authorization for operational endpoints, and never log payment method
        tokens or other sensitive values.
    - id: orders_db
      description: Primary database for order and payment-related records.
      kind: database
      technology: PostgreSQL
      responsibilities:
        - Store order records.
        - Store payment attempt records.
        - Support reads and writes required by ordering workflows.
      security: >
        Must only accept connections from approved application-layer clients and
        must protect persisted order and payment-related data at rest.
    - id: payment_gateway
      description: Payment processing API used to authorize and capture order payments.
      kind: external_container
      technology: Stripe API
      responsibilities:
        - Authorize payments.
        - Capture payments.
        - Return payment outcomes.
      security: >
        Must be called over provider-supported secure transport and used in
        accordance with provider authentication and secret-handling requirements.
  relationships:
    - from: storefront_web
      to: ordering_api
      description: Sends product, cart, and order requests over HTTPS JSON APIs.
    - from: ordering_api
      to: orders_db
      description: Reads and writes order and payment records using SQL.
    - from: ordering_api
      to: payment_gateway
      description: Sends payment authorization and capture requests over HTTPS.
```

## Runtime Flow

Defines how a high-level flow is executed across C4 containers by describing the payloads passed between containers at each step.

```yaml
schema: forge.v2.runtime_flow

runtime_flow:
  id: string
  high_level_flow: string
  description: string
  trigger: string
  steps:
    - id: number
      container: string
      description: string
      next: number
      outgoing: string
      branches:
        - condition: string
          next: number
          outgoing: string
  outcomes:
    - string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.runtime_flow`.

`runtime_flow.id`
- Canonical identifier for the runtime flow.
- Multi-word ids should use `snake_case`.

`runtime_flow.high_level_flow`
- Id of the high-level flow this runtime flow realizes.

`runtime_flow.description`
- Plain-language description of the runtime flow.
- This should explain how the high-level flow is realized across containers.

`runtime_flow.trigger`
- Exact payload definition that enters the first step in the flow.
- This may include field names, nested structure, required data, and data types.
- This should be precise enough for an agent to understand exactly what is being received.
- When the payload has been promoted into a `data_shape`, use `ref[data_shape_id]` instead of repeating the full structure inline.

`runtime_flow.steps`
- Ordered container-level steps in the flow.
- Each step represents one container participating in the flow.
- Internal processing inside a container is not modeled here.

`runtime_flow.steps[].id`
- Numeric identifier for the step.
- Step ids should be unique within the flow and should reflect ordering.

`runtime_flow.steps[].container`
- Id of the runtime container handling this step.

`runtime_flow.steps[].description`
- Plain-language description of what the container does at this step.

`runtime_flow.steps[].next`
- Numeric id of the normal next step.
- A step may define `next` or `branches`, but never both.
- Terminal steps should omit this field.

`runtime_flow.steps[].outgoing`
- Exact payload definition sent from this step to the next step.
- This may include field names, nested structure, required data, and data types.
- This should be precise enough for an agent to understand exactly what is being passed onward.
- When the payload has been promoted into a `data_shape`, use `ref[data_shape_id]` instead of repeating the full structure inline.
- A terminal step should omit this field.

`runtime_flow.steps[].branches`
- Optional list of decision branches from the current step.
- Use this when the step can lead to multiple different next steps.
- A step may define `branches` or `next`, but never both.

`runtime_flow.steps[].branches[].condition`
- Plain-language description of the condition that causes the branch.

`runtime_flow.steps[].branches[].next`
- Numeric id of the step that follows when the condition is met.

`runtime_flow.steps[].branches[].outgoing`
- Exact payload definition sent on that branch.
- This may include field names, nested structure, required data, and data types.
- When the payload has been promoted into a `data_shape`, use `ref[data_shape_id]` instead of repeating the full structure inline.

`runtime_flow.outcomes`
- Canonical outcomes produced by the runtime flow.

Additional rule:
- A step with `next` is a linear step.
- A step with `branches` is a decision step.
- A step with neither is a terminal step.
- A step with both is invalid.
- `next` and branch targets may point to earlier steps when the flow intentionally loops.

### Example

```yaml
schema: forge.v2.runtime_flow

runtime_flow:
  id: place_order_runtime
  high_level_flow: place_order
  description: >
    Realizes the place_order flow by moving order data from the storefront
    through the ordering backend, persistence layer, and payment integration.
  trigger: >
    {
      customer_id: string,
      line_items: [
        {
          product_id: string,
          quantity: integer
        }
      ],
      delivery_address: {
        line_1: string,
        line_2?: string,
        city: string,
        postcode: string,
        country_code: string
      },
      payment_method_token: string
    }
  steps:
    - id: 1
      container: storefront_web
      description: Validates the customer submission and forwards the order request to the backend.
      next: 2
      outgoing: >
        {
          customer_id: string,
          line_items: [
            {
              product_id: string,
              quantity: integer
            }
          ],
          pricing_summary: {
            subtotal_amount: decimal,
            currency: string
          },
          delivery_address: {
            line_1: string,
            line_2?: string,
            city: string,
            postcode: string,
            country_code: string
          },
          payment_method_token: string
        }
    - id: 2
      container: ordering_api
      description: Validates the order request and determines whether the order can proceed.
      branches:
        - condition: Order request is valid and can be persisted.
          next: 3
          outgoing: >
            {
              customer_id: string,
              line_items: [
                {
                  product_id: string,
                  quantity: integer
                }
              ],
              pricing_summary: {
                subtotal_amount: decimal,
                currency: string
              },
              delivery_address: {
                line_1: string,
                line_2?: string,
                city: string,
                postcode: string,
                country_code: string
              },
              payment_method_token: string,
              order_status: pending_payment
            }
        - condition: Order request is invalid and cannot proceed.
          next: 5
          outgoing: ref[order_rejection_response]
    - id: 3
      container: orders_db
      description: Persists the order and returns the stored order record to the backend.
      next: 4
      outgoing: ref[order_record]
    - id: 4
      container: ordering_api
      description: Uses the persisted order to request payment authorization and determine the final result.
      branches:
        - condition: Payment is authorized successfully.
          next: 6
          outgoing: ref[order_confirmation_response]
        - condition: Payment authorization fails.
          next: 5
          outgoing: ref[order_rejection_response]
    - id: 5
      container: storefront_web
      description: Displays the failure outcome to the customer.
    - id: 6
      container: storefront_web
      description: Displays the successful order confirmation to the customer.
  outcomes:
    - Order is accepted and confirmed to the customer.
    - Order is rejected and the customer is informed of the failure.
```

## Vertical

Defines a development-oriented vertical slice of the system. A vertical is an end-to-end build slice, not a business domain grouping.

```yaml
schema: forge.v2.vertical

verticals:
  - id: string
    description: string
    user_value: string
    high_level_flows:
      - string
    runtime_containers:
      - string
    data_shapes:
      - string
    persistent_shapes:
      - string
    deployment_notes: string
    build_notes: string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.vertical`.

`verticals`
- List of development-oriented vertical slices derived from the overall system model.
- A vertical represents an end-to-end implementation slice that can be built and delivered incrementally.

`verticals[].id`
- Canonical identifier for the vertical.
- Multi-word ids should use `snake_case`.

`verticals[].description`
- Plain-language description of what the vertical is.
- This should describe the slice in implementation terms, not as a broad business domain.

`verticals[].user_value`
- Plain-language description of the usable end-to-end value this vertical delivers.

`verticals[].high_level_flows`
- List of `high_level_flow` ids covered by the vertical.
- These should reference flows already defined in the system model.

`verticals[].runtime_containers`
- List of runtime container ids involved in delivering the vertical.
- These may be empty when the vertical is first initialized and filled in as the vertical is elaborated.

`verticals[].data_shapes`
- List of promoted `data_shape` ids used by the vertical.
- These may be empty when the vertical is first initialized and filled in later only where promotion is justified.

`verticals[].persistent_shapes`
- List of `persistent_shape` ids used by the vertical.
- These may be empty when the vertical is first initialized and filled in as persisted state becomes explicit.

`verticals[].deployment_notes`
- Plain-language notes about any deployment concerns relevant to the vertical.
- This may begin rough and become more precise later.

`verticals[].build_notes`
- Plain-language notes about how the vertical should be built, sequenced, or constrained as an implementation slice.
- This may begin rough and become more precise later.

### Example

```yaml
schema: forge.v2.vertical

verticals:
  - id: place_order
    description: End-to-end implementation slice for customer checkout and order placement.
    user_value: Customers can submit an order and receive a confirmed or rejected result.
    high_level_flows:
      - place_order
    runtime_containers:
      - storefront_web
      - ordering_api
      - orders_db
      - payment_gateway
    data_shapes:
      - order_record
      - order_confirmation_response
      - order_rejection_response
    persistent_shapes:
      - order
      - payment_attempt
    deployment_notes: >
      Requires the storefront, ordering API, primary order database, and payment
      gateway integration to be available in the target environment.
    build_notes: >
      Build this vertical by first making the checkout submission reach the
      ordering API, then add persistence, then add payment authorization, and
      finally return the customer-facing success and failure responses.
```

## Data Shape

Defines an important reusable exact data structure. A data shape can represent a payload or a stored shape the system cares about enough to name explicitly.

```yaml
schema: forge.v2.data_shape

data_shapes:
  - id: string
    description: string
    kind: enum[payload, state]
    shape: object
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.data_shape`.

`data_shapes`
- List of important reusable exact data definitions.
- Not every payload needs to become a `data_shape`.
- A `data_shape` should exist when the data is important enough, reused enough, or stable enough to deserve a named definition.
- A payload or stored object should only be promoted into a `data_shape` when it is reused, persisted, or otherwise important enough to require a stable named definition. Otherwise it should remain inline in the flow.
- Once promoted, flows should prefer `ref[data_shape_id]` instead of repeating the same structure inline.

`data_shapes[].id`
- Canonical identifier for the data shape.
- Multi-word ids should use `snake_case`.

`data_shapes[].description`
- Plain-language description of what the data shape represents.

`data_shapes[].kind`
- The general role of the data shape.
- Allowed values:
  - `payload`
  - `state`

`data_shapes[].shape`
- Exact structure of the data shape.
- This should stay compact and readable.
- Use nested YAML directly for nested objects.
- Use a YAML list for arrays.
- Use inline constraints when needed.

Allowed primitive types:
- `string`
- `integer`
- `decimal`
- `boolean`
- `datetime`
- `vector`

Allowed conventions inside `shape`:

Optional field:

```yaml
line_2?: string
```

Nested object:

```yaml
delivery_address:
  line_1: string
  city: string
  postcode: string
```

Array:

```yaml
line_items:
  - product_id: string
    quantity: integer
```

Enum:

```yaml
status: enum[pending, confirmed, rejected]
```

Reference to another promoted data shape:

```yaml
customer: ref[customer]
```

Inline constraints:

```yaml
email: string @regex(^.+@.+\..+$)
quantity: integer @min(1)
discount_percent?: decimal @min(0) @max(100)
country_code: string @enum[AU, NZ, US]
embedding: vector @dimensions(1536)
```

### Example

```yaml
schema: forge.v2.data_shape

data_shapes:
  - id: order_confirmation_response
    description: Customer-facing success response returned when an order is confirmed.
    kind: payload
    shape:
      order_id: string
      status: enum[confirmed]
      payment_status: enum[authorized]
      confirmation_message: string

  - id: order_rejection_response
    description: Customer-facing failure response returned when an order cannot proceed.
    kind: payload
    shape:
      order_id?: string
      status: enum[rejected]
      payment_status?: enum[failed]
      failure_reason?: string
      errors?:
        - field: string
          message: string
      user_message: string

  - id: product_embedding
    description: Stored vector representation of a product for semantic search.
    kind: state
    shape:
      product_id: string
      embedding: vector @dimensions(1536)
      model: string
      generated_at: datetime

  - id: order_record
    description: Persisted order shape stored after checkout is accepted.
    kind: state
    shape:
      order_id: string
      customer_id: string
      line_items:
        - product_id: string
          quantity: integer @min(1)
      pricing_summary:
        subtotal_amount: decimal
        currency: string
      delivery_address:
        line_1: string
        line_2?: string
        city: string
        postcode: string
        country_code: string @enum[AU, NZ, US]
      order_status: enum[pending_payment, confirmed, fulfilled, cancelled, failed]
      persisted_at: datetime

  - id: payment_attempt_record
    description: Persisted record of a single payment authorization attempt for an order.
    kind: state
    shape:
      payment_attempt_id: string
      order_id: string
      payment_status: enum[initiated, authorized, failed]
      failure_reason?: string
      attempted_at: datetime
```

## Persistent Shape

Defines the persisted subset of important data shapes: where they are owned, where they are stored, how they are persisted, and how they behave through their lifecycle.

```yaml
schema: forge.v2.persistent_shape

persistent_shapes:
  - id: string
    description: string
    data_shape: string
    logical_owner_container: string
    data_store_container: string
    storage_model: enum[relational, document, key_value, vector, time_series, graph, blob, file_system]
    persistence_behavior: string
    lifecycle_status_notes: string
    security: string
    state_machine:
      states:
        - string
      transitions:
        - from: string
          to: string
          condition: string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.persistent_shape`.

`persistent_shapes`
- List of persisted, architecturally significant shapes.
- Every `persistent_shape` must reference a `data_shape`.
- Not every `data_shape` becomes a `persistent_shape`.

`persistent_shapes[].id`
- Canonical identifier for the persisted shape.
- Multi-word ids should use `snake_case`.

`persistent_shapes[].description`
- Plain-language description of what this persisted shape represents.

`persistent_shapes[].data_shape`
- Reference to the exact reusable `data_shape` used by this persisted shape.

`persistent_shapes[].logical_owner_container`
- Id of the container that logically owns this persisted shape.

`persistent_shapes[].data_store_container`
- Id of the container where this persisted shape is physically stored.

`persistent_shapes[].storage_model`
- The persistence model used for this shape.
- Allowed values:
  - `relational`
  - `document`
  - `key_value`
  - `vector`
  - `time_series`
  - `graph`
  - `blob`
  - `file_system`

`persistent_shapes[].persistence_behavior`
- Plain-language description of how the shape is written, updated, retained, queried, or replaced.

`persistent_shapes[].lifecycle_status_notes`
- Plain-language description of the lifecycle or status behavior of the persisted shape.

`persistent_shapes[].security`
- Plain-language description of the security requirements for the persisted shape itself.
- Use this for encryption, retention, masking, access sensitivity, auditability, or other data-protection rules specific to the persisted shape.

`persistent_shapes[].state_machine`
- Optional formal lifecycle model for the persisted shape.
- Use this only when explicit state transitions matter.

`persistent_shapes[].state_machine.states`
- List of lifecycle states for the persisted shape.

`persistent_shapes[].state_machine.transitions`
- List of state transitions for the persisted shape.

`persistent_shapes[].state_machine.transitions[].from`
- Starting state for the transition.

`persistent_shapes[].state_machine.transitions[].to`
- Ending state for the transition.

`persistent_shapes[].state_machine.transitions[].condition`
- Plain-language condition under which the transition occurs.

### Example

```yaml
schema: forge.v2.persistent_shape

persistent_shapes:
  - id: order
    description: Persisted order shape representing a customer's purchase through its lifecycle.
    data_shape: order_record
    logical_owner_container: ordering_api
    data_store_container: orders_db
    storage_model: relational
    persistence_behavior: >
      Orders are created when checkout succeeds, updated as payment and fulfillment
      progress, and queried by customer-facing and operational workflows.
    lifecycle_status_notes: >
      Orders move through pending payment, confirmed, fulfilled, cancelled, or failed
      states depending on payment and fulfillment outcomes.
    security: >
      Contains customer and order data that must be encrypted at rest, exposed
      only to approved application workflows, and masked appropriately in
      operator-facing views.
    state_machine:
      states:
        - pending_payment
        - confirmed
        - fulfilled
        - cancelled
        - failed
      transitions:
        - from: pending_payment
          to: confirmed
          condition: Payment is authorized successfully.
        - from: pending_payment
          to: failed
          condition: Payment authorization fails.
        - from: confirmed
          to: fulfilled
          condition: Fulfillment is completed successfully.
        - from: confirmed
          to: cancelled
          condition: The order is cancelled before fulfillment completes.

  - id: payment_attempt
    description: Persisted payment attempt shape used to record each authorization attempt for an order.
    data_shape: payment_attempt_record
    logical_owner_container: ordering_api
    data_store_container: orders_db
    storage_model: relational
    persistence_behavior: >
      Payment attempts are written whenever the ordering API tries to authorize
      payment and are queried for order progress, retries, and failure analysis.
    lifecycle_status_notes: >
      Payment attempts move from initiated to authorized or failed depending on
      the payment outcome returned by the payment provider.
    security: >
      Must retain an auditable history of payment outcomes without storing raw
      payment credentials or provider secrets.
    state_machine:
      states:
        - initiated
        - authorized
        - failed
      transitions:
        - from: initiated
          to: authorized
          condition: Payment provider returns a successful authorization result.
        - from: initiated
          to: failed
          condition: Payment provider returns a failure result.
```

## Container

Defines the internal C4 component structure of a single container and how data moves between those components when realizing part of a runtime flow.

```yaml
schema: forge.v2.container

container:
  id: string
  description: string
  components:
    - id: string
      description: string
      responsibilities:
        - string
  component_flows:
    - id: string
      runtime_flow: string
      description: string
      trigger: string
      steps:
        - id: number
          component: string
          description: string | list[string]
          next: number
          outgoing: string
          branches:
            - condition: string
              next: number
              outgoing: string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.container`.

`container`
- Internal component model for one important runtime container.
- Components are not deployable units. They are internal groupings of related functionality inside a container.

`container.id`
- Canonical identifier for the container.
- Multi-word ids should use `snake_case`.

`container.description`
- Plain-language description of the container's internal structure and why it is modeled explicitly.

`container.components`
- List of meaningful internal functional groupings inside the container.
- A component is a grouping of related functionality encapsulated behind a well-defined interface.

`container.components[].id`
- Canonical identifier for the component.
- Multi-word ids should use `snake_case`.

`container.components[].description`
- Plain-language description of what the component is and what role it plays inside the container.

`container.components[].responsibilities`
- List of the main responsibilities owned by the component.

`container.component_flows`
- List of internal flows between components inside the container.
- These flows zoom in on part of a `runtime_flow`.

`container.component_flows[].id`
- Canonical identifier for the component flow.
- Multi-word ids should use `snake_case`.

`container.component_flows[].runtime_flow`
- Id of the runtime flow this component flow refines.

`container.component_flows[].description`
- Plain-language description of the component flow.

`container.component_flows[].trigger`
- Exact payload definition that enters the first step in the component flow.
- This may include field names, nested structure, required data, and data types.
- When the payload has been promoted into a `data_shape`, use `ref[data_shape_id]` instead of repeating the full structure inline.

`container.component_flows[].steps`
- Ordered component-level steps in the flow.
- Each step represents one component participating in the internal flow.

`container.component_flows[].steps[].id`
- Numeric identifier for the step.
- Step ids should be unique within the flow and should reflect ordering.

`container.component_flows[].steps[].component`
- Id of the component handling this step.

`container.component_flows[].steps[].description`
- Description of what the component does at this step.
- This may be:
  - a plain string
  - a list of strings representing the internal stepped logic inside the component

`container.component_flows[].steps[].next`
- Numeric id of the normal next step.
- A step may define `next` with optional `outgoing`, or `branches`, but never both.
- Terminal steps should omit this field.

`container.component_flows[].steps[].outgoing`
- Exact payload definition emitted by this step.
- For a step with `next`, this is the payload sent to the next component step.
- For a terminal step without `next` or `branches`, this is the payload emitted back to the runtime/container boundary.
- This may include field names, nested structure, required data, and data types.
- When the payload has been promoted into a `data_shape`, use `ref[data_shape_id]` instead of repeating the full structure inline.
- A step may define `next` with optional `outgoing`, `branches`, or terminal `outgoing`, but never mix linear and branch fields.

`container.component_flows[].steps[].branches`
- Optional list of decision branches from the current step.
- Use this when the step can lead to multiple different next steps.
- A step may define `branches`, or `next` with optional `outgoing`, but never both.

`container.component_flows[].steps[].branches[].condition`
- Plain-language description of the condition that causes the branch.

`container.component_flows[].steps[].branches[].next`
- Numeric id of the step that follows when the condition is met.

`container.component_flows[].steps[].branches[].outgoing`
- Exact payload definition sent on that branch.
- This may include field names, nested structure, required data, and data types.
- When the payload has been promoted into a `data_shape`, use `ref[data_shape_id]` instead of repeating the full structure inline.

Additional rule:
- A step with `next` is a linear step and may include `outgoing`.
- A step with `branches` is a decision step.
- A step with neither `next` nor `branches` is a terminal step and may include `outgoing`.
- A step with both linear and branch fields is invalid.
- `next` and branch targets may point to earlier steps when the component flow intentionally loops.

### Example

```yaml
schema: forge.v2.container

container:
  id: ordering_api
  description: >
    Internal component structure for the ordering API, showing how order
    requests are validated, persisted, and turned into customer-facing outcomes.
  components:
    - id: order_request_controller
      description: Entry component for storefront order requests.
      responsibilities:
        - Accept order submission requests.
        - Forward validated input into the ordering workflow.
    - id: order_validation_service
      description: Validates order requests and prepares them for persistence.
      responsibilities:
        - Validate incoming order data.
        - Normalize order content for downstream processing.
    - id: order_repository
      description: Persists and retrieves order state from the primary data store.
      responsibilities:
        - Write order records.
        - Read stored order records.
    - id: payment_service
      description: Coordinates payment authorization for persisted orders.
      responsibilities:
        - Send payment authorization requests.
        - Interpret payment outcomes.
    - id: order_response_mapper
      description: Builds customer-facing success and failure responses.
      responsibilities:
        - Construct confirmation responses.
        - Construct rejection responses.
  component_flows:
    - id: place_order_internal
      runtime_flow: place_order_runtime
      description: >
        Realizes the ordering_api portion of the place_order runtime flow.
      trigger: >
          {
            customer_id: string,
            line_items: [
              {
                product_id: string,
                quantity: integer
              }
            ],
            pricing_summary: {
              subtotal_amount: decimal,
              currency: string
            },
            delivery_address: {
              line_1: string,
              line_2?: string,
              city: string,
              postcode: string,
              country_code: string
            },
            payment_method_token: string
          }
      steps:
        - id: 1
          component: order_request_controller
          description:
            - Accept the order request from the storefront.
            - Perform request-level validation checks.
            - Pass the normalized request into the validation service.
          next: 2
          outgoing: >
              {
                customer_id: string,
                line_items: [
                  {
                    product_id: string,
                    quantity: integer
                  }
                ],
                pricing_summary: {
                  subtotal_amount: decimal,
                  currency: string
                },
                delivery_address: {
                  line_1: string,
                  line_2?: string,
                  city: string,
                  postcode: string,
                  country_code: string
                },
                payment_method_token: string
              }
        - id: 2
          component: order_validation_service
          description:
            - Validate the business correctness of the request.
            - Normalize order content for persistence.
            - Decide whether the order can proceed.
          branches:
            - condition: Order request is valid and can be persisted.
              next: 3
              outgoing: >
                  {
                    customer_id: string,
                    line_items: [
                      {
                        product_id: string,
                        quantity: integer
                      }
                    ],
                    pricing_summary: {
                      subtotal_amount: decimal,
                      currency: string
                    },
                    delivery_address: {
                      line_1: string,
                      line_2?: string,
                      city: string,
                      postcode: string,
                      country_code: string
                    },
                    payment_method_token: string,
                    order_status: pending_payment
                  }
            - condition: Order request is invalid and cannot proceed.
              next: 5
              outgoing: ref[order_rejection_response]
        - id: 3
          component: order_repository
          description: Persist the order and return the stored record for payment processing.
          next: 4
          outgoing: ref[order_record]
        - id: 4
          component: payment_service
          description:
            - Request payment authorization for the persisted order.
            - Determine whether the order can be confirmed.
          branches:
            - condition: Payment is authorized successfully.
              next: 5
              outgoing: ref[order_confirmation_response]
            - condition: Payment authorization fails.
              next: 5
              outgoing: ref[order_rejection_response]
        - id: 5
          component: order_response_mapper
          description:
            - Build the customer-facing response payload.
            - Return the final result to the calling container boundary.
```

## Deployment

Defines where runtime containers are placed in real environments and records the deployment-specific notes needed to understand that topology.

```yaml
schema: forge.v2.deployment

deployment:
  environments:
    - id: string
      description: string
      nodes:
        - id: string
          description: string
          kind: string
          technology: string
          containers:
            - string
          endpoint: string
          region: string
          scaling_notes: string
          availability_notes: string
          depends_on:
            - string
          trust_boundary: string
```

### Field Rules

`schema`
- Reference string identifying the schema being authored.
- For this artifact, the value is `forge.v2.deployment`.

`deployment`
- The overall deployment model for the system.
- This describes where runtime containers are placed in real environments.

`deployment.environments`
- List of deployment environments.
- Each environment is a separate runtime context such as `local`, `staging`, or `production`.

`deployment.environments[].id`
- Canonical identifier for the environment.
- Multi-word ids should use `snake_case`.

`deployment.environments[].description`
- Plain-language description of what the environment is for.

`deployment.environments[].nodes`
- List of deployment nodes in the environment.
- A node is a real place where one or more containers run.

`deployment.environments[].nodes[].id`
- Canonical identifier for the node.
- Multi-word ids should use `snake_case`.

`deployment.environments[].nodes[].description`
- Plain-language description of the node and its role in the environment.

`deployment.environments[].nodes[].kind`
- General category of deployment node.
- Example values might include `browser`, `serverless_runtime`, `managed_database`, `cdn`, `vm`, or `kubernetes_service`.

`deployment.environments[].nodes[].technology`
- Actual platform, runtime, or product used by the node.

`deployment.environments[].nodes[].containers`
- List of runtime container ids deployed on the node.
- These should reference the containers defined in the `runtime` artifact.

`deployment.environments[].nodes[].endpoint`
- Relevant access point for the node where applicable.
- This may be a URL, hostname, internal DNS name, or similar deployment endpoint.

`deployment.environments[].nodes[].region`
- Geographic or logical region where the node runs.

`deployment.environments[].nodes[].scaling_notes`
- Plain-language description of how the node scales or is expected to scale.

`deployment.environments[].nodes[].availability_notes`
- Plain-language description of resilience, redundancy, or availability characteristics for the node.

`deployment.environments[].nodes[].depends_on`
- List of other deployment node ids this node depends on.

`deployment.environments[].nodes[].trust_boundary`
- Plain-language label for the security or network trust zone this node sits within.
- A trust boundary marks where security or trust assumptions change.

### Example

```yaml
schema: forge.v2.deployment

deployment:
  environments:
    - id: production
      description: Live production environment serving customer traffic.
      nodes:
        - id: customer_browser
          description: Browser runtime where the storefront web application executes for customers.
          kind: browser
          technology: Customer web browser
          containers:
            - storefront_web
          endpoint: https://shop.example.com
          region: global
          scaling_notes: Scales with concurrent customer usage automatically on the client side.
          availability_notes: Availability depends on customer device and internet access.
          depends_on:
            - storefront_edge
          trust_boundary: public_client_environment

        - id: storefront_edge
          description: Edge delivery node serving the storefront application assets.
          kind: cdn
          technology: CloudFront
          containers:
            - storefront_web
          endpoint: https://shop.example.com
          region: global
          scaling_notes: Scales automatically with customer traffic volume.
          availability_notes: Multi-edge delivery with provider-managed failover.
          depends_on:
            - ordering_api_runtime
          trust_boundary: public_edge_network

        - id: ordering_api_runtime
          description: Hosted backend runtime serving ordering APIs and coordinating order workflows.
          kind: kubernetes_service
          technology: Kubernetes on AWS
          containers:
            - ordering_api
          endpoint: https://api.example.com
          region: ap-southeast-2
          scaling_notes: Horizontally scales based on API load and request volume.
          availability_notes: Runs across multiple replicas and availability zones.
          depends_on:
            - orders_database
            - payment_provider_gateway
          trust_boundary: private_application_network

        - id: orders_database
          description: Managed relational database runtime storing order and payment state.
          kind: managed_database
          technology: PostgreSQL on Amazon RDS
          containers:
            - orders_db
          endpoint: orders-db.internal
          region: ap-southeast-2
          scaling_notes: Scales vertically with provisioned capacity and read replicas as needed.
          availability_notes: Multi-AZ deployment with automated backups.
          depends_on: []
          trust_boundary: private_data_tier

        - id: payment_provider_gateway
          description: Third-party payment API endpoint used for payment authorization and capture.
          kind: external_api
          technology: Stripe API
          containers:
            - payment_gateway
          endpoint: https://api.stripe.com
          region: provider_managed
          scaling_notes: Scales according to provider capacity.
          availability_notes: Availability is subject to third-party provider SLAs.
          depends_on: []
          trust_boundary: third_party_boundary
```
