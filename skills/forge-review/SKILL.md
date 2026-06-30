---
name: forge-review
description: Review the Forge V4 merged model for consistency, broken references, unclear boundaries, flow mistakes, over-modeling, code/schema drift, audit readability, and missing or malformed C3 annotations. Use when the user wants a quality gate for central Forge V4 schema, extracted code-owned C3, a build slice, or the full system model, especially after editing forge/system.yaml, forge/containers.yaml, forge/entities.yaml, forge/crawler.yaml, or @forge annotations, and before forge-build starts implementation.
---

# forge-review

Read before starting:

- `../../FRAMEWORK_V4.md`
- `../../SCHEMA_REFERENCE_V4.md`

Prefer when available:

- `forge crawl --format json`
- `forge context`
- `forge knowledge list`
- `forge audit`

## Purpose

Review the Forge V4 model that actually exists.

Forge V4 truth is the merged result of:

```text
central C1/C2 schema
+ code-owned C3 annotations
+ crawler validation findings
```

This skill should find risks and defects. It should not silently redesign the
system. If a fix requires new architecture, route back to `forge-schema`.

## Knowledge Layer

When reviewing a system, container, flow, entity, component, or operation, use
`forge knowledge list --ref <kind>:<id>` to inspect attached runbooks, test
suites, deployment notes, security notes, incidents, migrations, and guides.
Review stale or contradictory docs as drift findings. Knowledge docs support
the review but do not override the merged Forge model.

## Decision Log

Read `forge/decisions.yaml` when it exists and use it as review context.

Record or request a decision entry when review accepts a non-trivial trade-off,
deferral, modeling exception, source-root/layout choice, known drift, or
residual risk. Use the `forge.decisions` schema from `SCHEMA_REFERENCE_V4.md`.

Review findings should call out missing decision records when an architectural
choice is visible in schema or code but the rationale is not crawlable.

## Output Standard

Lead with findings.

Order findings by severity:

1. Broken extraction, malformed schema, or broken references
2. Broken input/return contracts across runtime or C3 flow steps
3. Behaviorally misleading architecture
4. Missing or misleading C3 annotations
5. Security, privacy, or trust-boundary gaps
6. Over-modeling, under-modeling, or unclear ownership
7. Context or audit readability issues

Every finding should include:

- evidence
- impact
- smallest fix direction
- owner skill: `forge-schema`, `forge-security`, or `forge-build`

If no issues are found, say so clearly and note any residual risk.

## Complexity Review

When reviewing build, schema, or annotation changes, also run a complexity pass:

- `delete`: dead schema, unused annotation, speculative feature, stale option
- `stdlib`: custom code where the language/platform already provides the behavior
- `native`: dependency or model construct doing what the runtime, database, browser, or Forge crawler already does
- `yagni`: abstraction, container, config, helper, flow, or decision record with only one real use
- `shrink`: same contract or behavior can be represented with fewer files, annotations, or schema elements

Prefer one-line findings:

```text
path:line: yagni: one-use adapter around a single operation. Inline until a second caller exists.
```

Do not apply fixes during review unless the user asks for a fix pass. End with a
rough net impact when useful: `net: -N lines/files/schema elements possible`.

## Workflow

### 1. Establish Scope

Identify whether the review is for:

- full system
- one container
- one flow
- one entity
- one component or operation
- one build slice

Do not broaden scope unless the requested target cannot be evaluated safely
without more context.

### 2. Load The Merged Model

Start with:

```bash
forge crawl --format json
```

Use crawler output as the source of truth for:

- central system, containers, container flows, and entities
- extracted components, data shapes, persistence, and operations
- warnings and validation findings
- source locations for annotations

If crawl fails, report the failure first and stop the review there.

### 3. Pull Focused Context

Use scoped context only as needed:

```bash
forge context --system --format md
forge context --container <id> --format md
forge context --flow <id> --format md
forge context --entity <id> --format md
forge context --component <id> --format md
forge context --operation <id> --format md
forge context --data-shape <id> --format md
```

Use `forge audit` when a human-facing review surface or diagram readability is
part of the request.

## Review Checks

### Central C1/C2

Check:

- `system.yaml` describes system intent, not implementation mechanics.
- Business actions are intent and outcomes, not runtime steps.
- Actors and external dependencies are real and referenced correctly.
- Containers are real runtime/deployment units.
- Container responsibilities do not overlap confusingly.
- Container flows describe cross-container runtime control, not C3 internals.
- Flow steps use `next`, `branches`, or terminal form correctly.
- Entities are business-significant, not incidental DTOs.
- Entity ownership, canonical type, persistence, lifecycle, and security are not conflated.

### Code-Owned C3

Check:

- Architecture-significant code has nearby `@forge:*` annotations.
- Components represent meaningful interfaces, logic, persistence, datastores, adapters, or utilities.
- Operations describe code contracts and participation in container/local flows.
- Data shapes represent important reusable or canonical shapes.
- Persistence annotations match real durable storage behavior.
- Annotation container/component inference from `source_root` is correct.
- Duplicate or malformed annotations are treated as blocking findings.

### Boundary Discipline

Check:

- C1/C2 central files do not model inside-container/component flow.
- C3 annotations do not contradict central container or entity ownership.
- Same-container local work is summarized centrally and detailed in C3.
- Runtime containers are not created from domain nouns alone.
- Shared/global concepts are justified by real reuse.

### Drift And Completeness

Check:

- Referenced ids resolve across central schema and extracted annotations.
- Container flows reference known business actions and containers.
- Entity canonical types point to known or intentionally planned data shapes.
- Persisted entities point to real persistence ownership.
- Code behavior and model claims appear aligned.
- The first build slice is thin enough to implement and validate.

### Contract Continuity

Explicitly evaluate every input and return/output contract for every step of
every runtime/container flow.

For each `container_flows[].steps[]`, check:

- The trigger input is sufficient for the first step.
- Each step input can be produced by the trigger, a prior step output, retained
  in-flight workflow state, reloaded durable state, or an external dependency.
- Each step output is sufficient for every downstream `next` or `branches`
  target that depends on it.
- Branch conditions have access to the state they inspect.
- Branch outputs are compatible with the target step input.
- Terminal outcomes are supported by the final step outputs.
- Same-container retained workflow context is explicit when later steps depend
  on earlier same-container knowledge that is not present in the immediate
  boundary payload.

For each extracted `@forge:operation`, check:

- `input` matches the contract the operation needs from its participating
  container/local flow step.
- `returns` matches what the next local operation, runtime step, caller, or
  terminal outcome expects.
- `logic` does not claim to read fields that are absent from `input`, retained
  context, durable state, or external dependencies.
- `participates_in.container_flow` points to the correct runtime step.
- `participates_in.local_flow`, `passes`, and `flow_logic` describe local
  operation sequencing without contradicting the runtime step contract.

Raise a finding when a value appears from nowhere, disappears before it is
needed, changes shape without explanation, or crosses a container boundary
without an explicit output/input handoff.

### Human Review Quality

Check:

- `forge context` returns useful scoped output for the target.
- `forge audit` renders the model in a way a human can inspect.
- Diagrams show runtime containers as nodes and control movement as edges.
- Dense details live outside diagrams or behind progressive disclosure.

## Routing

Route fixes to:

- `forge-schema` for system intent, runtime containers, entities, or flow shape
- `forge-security` for auth, trust boundaries, sensitive data, retention, and compliance
- `forge-build` for missing implementation, tests, C3 annotations, or code/model drift

Do not patch architecture during review unless the user explicitly asks for a
fix pass.

## Guardrails

- Review the model Forge extracts, not the model that was intended.
- Do not accept bloat because it is structurally valid.
- Do not invent missing architecture to make a finding disappear.
- Do not flag personal style preferences as defects.
- Prefer a short findings list over a long recap.
