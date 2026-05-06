---
name: forge-spec
description: >
  Forge element elicitation skill. Use when system design is complete (forge-design has run)
  and the user wants to spec out one or more modules in detail. Drives a hybrid elicitation interview
  that fully understands a module's shape before assembling any files, builds types/errors/policies
  inline as they emerge, promotes them to registries when shared, then composes interactions into flows.
  Also produces concrete datastores and environments entries.
  Triggers on: "spec out this module", "let's define the elements", "forge-spec", or any request
  to elicit element/operation/contract detail within an existing Forge design.
---

# forge-spec

Read `references/framework.md` before starting — you need the full schema. Also read `workbench/discovery.md` and the target `module.yaml` before asking any questions.

## Purpose

Fully elicit one module at a time. Ask all the questions needed to understand the module's complete shape **before** writing any files. Then assemble everything in one pass.

**Hybrid elicitation model**: ask meaningful targeted questions to extract the most detail, build from the answers, then follow up with implementation-specificity questions to fill in fine-grained detail. Don't ask questions you can infer from discovery notes or prior answers.

## Output Artifacts (per module)

| File | Contents |
|------|----------|
| `spec/<system>/<domain>/<module>/<element>.yaml` | One per element, with inline properties + operations |
| `spec/<system>/types/<TypeName>.yaml` | One per promoted type |
| `spec/<system>/errors/<ErrorName>.yaml` | One per promoted error |
| `spec/<system>/policies/<policy>.yaml` | One per policy |
| `spec/<system>/contracts/<contract>.yaml` | One per contract |
| `spec/<system>/integrations/<integration>.yaml` | One per external integration |
| `spec/<system>/interactions/<interaction>.yaml` | One per operation-to-operation call |
| `spec/<system>/flows/<flow>.yaml` | One per named business flow |
| `spec/<system>/implementation/datastores.yaml` | Concrete datastore entries for this module |
| `spec/<system>/implementation/environments.yaml` | Concrete environment entries (if not yet written) |

## Elicitation Process

### Pre-read

Before asking anything:
1. Read `workbench/discovery.md` — extract what's already known about this module.
2. Read `module.yaml` — note packaging, runtime, external dependencies.
3. Run `forge list --kind element` to see what's already been defined across the system (reuse check).

### Phase 1 — Module Shape Interview

Ask all questions in this phase before writing anything. Batch questions that don't depend on each other.

**Entities and ownership**
- What are the core things this module manages? (aggregates, entities, value objects, services)
- For each: what state does it hold? What's its identity? What's its lifecycle?

**Operations**
- What can each entity do? (commands that change state, queries that read state, async variants, event handlers)
- For each operation: what goes in, what comes out, what can go wrong?
- Which operations are called by other modules? Which are internal only?

**Contracts and protocols**
- What does this module expose to other modules or external callers?
- What protocol? (REST, gRPC, queue, event_bus, etc.)
- Who are the consumers of each contract?

**Dependencies and integrations**
- What does this module call in other modules?
- What external services does it depend on? (already listed in module.yaml?)

**Data**
- What does this module persist? Where? (relational, document, cache, etc.)
- What engine? (postgres, redis, etc.)
- What's the read/write pattern per entity?

**Policies**
- Which operations require authentication? What mechanism?
- Are there rate limits, SLAs, or retry policies?
- Any data classification, retention, or audit requirements?

**Events**
- What events does this module emit? What events does it consume?

### Phase 2 — Implementation Detail

After Phase 1 answers are in, drill into specifics that the implementation will need:

- For each operation's inputs: what are the exact fields? Types? Constraints?
- For composite types: what are the fields? Optional vs required? Defaults?
- For errors: what's the HTTP status? Are there extra fields (e.g. `field_name` on validation errors)?
- For policies: what's the exact auth rule? Which roles?
- For datastores: what's the table/collection/key structure? What's the consistency requirement?

Ask only what you can't confidently infer. If the answer is obvious from context, default it and note it.

## Assembly Rules

### Types and Errors — inline emergence

- Define types and errors inline within element files as you encounter them.
- Run `forge find <name>` before creating any new type or error — surface potential reuse.
- **Promote to registry** (`types/` or `errors/`) when a type or error is referenced by more than one element or is part of a contract.
- Built-in scalars (`String`, `Integer`, `Float`, `Boolean`, `Timestamp`, `UUID`, `Blob`) and built-in errors (`NotFound`, `Unauthorized`, `Forbidden`, `Conflict`, `ValidationFailed`, `Unavailable`, `Timeout`) are referenced directly — never redefined.

### Registry Cleanup (end of module)

After assembling all elements, do one pass:
- Deduplicate any type or error that appears more than once inline — extract to registry.
- Ensure all `contract` fields on operations point to a real contract file.
- Ensure all policy IDs on elements and operations exist in `policies/`.

### Interactions and Flows

- Define one `interaction` node for each directed call between two operations.
- After all interactions are defined, compose them into `flow` nodes that represent named business processes.
- Flows must trace all the way down to interactions — no abstract steps.
- Assign `parallel_group` to interactions that can run concurrently within a flow.
- Define `on_failure` and `compensation` for any interaction that mutates state.

### Datastores

Write concrete entries to `implementation/datastores.yaml`:
- Exact `engine` (e.g. `postgres`, not just `relational`)
- Schema entries mapping element types to storage names (table, collection, key prefix)
- `consumers` list referencing this module

### Environments

Write concrete entries to `implementation/environments.yaml` if not already present:
- One entry per environment type established in design
- Exact `region`
- Per-datastore `connection` (secrets reference format, e.g. `${{ secrets.DB_URL }}`) and `instance_class`

## Module Completion

When all files are written:
1. Run `forge validate` — resolve any structural errors before proceeding.
2. Update the module's `elements` list in `module.yaml`.
3. State which module was completed and ask whether to continue with the next module or stop.

## Key Constraints

- Never write an element file until Phase 1 and Phase 2 are complete for that module.
- Never invent structure the human hasn't confirmed. Draft and ask if unsure.
- `workbench/` files are never modified by this skill — read-only.
- One module at a time. Full elicitation before moving to the next.
