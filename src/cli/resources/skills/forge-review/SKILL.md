---
name: forge-review
description: Review Forge V2 schema artifacts for consistency, bloat, broken references, bad promotion decisions, flow mistakes, security gaps, and deployment/runtime drift. Use when the user wants a review of any Forge V2 schema scope, vertical slice, or full system model, especially after authoring `system`, `flows`, `runtime`, `verticals`, `data_shapes`, `persistent_shapes`, `container`, or `deployment`, and before `forge-build` starts implementation.
---

# forge-review

Read before starting:

- `../../SCHEMA_REFERENCE_V3.md`

## Purpose

Review the produced Forge V2 artifacts and return findings.

This skill should:

1. Find structural inconsistencies.
2. Find anti-bloat violations.
3. Find unclear or invalid flow logic.
4. Find promotion mistakes around `data_shape` and `persistent_shape`.
5. Find security and deployment drift.

For a vertical that is about to be implemented, this skill should act as a pre-build readiness pass rather than an after-the-fact cleanup step.

Do not silently rewrite the architecture in review. Prefer findings, rationale, and routing back to the right authoring stage.

## Review Output Standard

Present findings first.

Order findings by severity:

1. structural invalidity
2. behaviorally misleading architecture
3. security or trust-boundary gaps
4. over-modeling and schema bloat
5. quality or clarity issues

Every finding should include:

- what is wrong
- why it matters
- which artifact or stage it belongs to
- what the likely fix direction is

If nothing is wrong, say so explicitly and then note any remaining risks or modeling gaps.

## Review Modes

Use one of these modes based on scope.

### Full-System Review

Review the whole chain:

- `system`
- `high_level_flow`
- `early_state`
- `runtime`
- `vertical`
- `runtime_flow`
- `data_shape`
- `persistent_shape`
- `container`
- `deployment`

### Vertical Review

Review one chosen vertical across:

- `vertical`
- matching `runtime_flow`
- related `data_shape`
- related `persistent_shape`
- related `container`
- relevant `deployment`

### Stage Review

Review only one artifact class when the user asks for a narrower pass.

## Review Workflow

1. Identify the scope being reviewed.
2. Read only the relevant artifacts for that scope.
3. Validate references and stage ordering first.
4. Validate behavior and modeling discipline second.
5. Validate security and deployment coherence third.
6. Present findings.

If a fix would require inventing new architecture rather than correcting drift, route back to `forge-schema` instead of improvising in review.

## LLM Review Guardrails

Apply these safeguards during every review:

1. Findings must be grounded in a schema rule, artifact line, broken reference, or concrete behavioral risk.
2. Do not invent fixes that require new architecture; identify the smallest correction direction.
3. Do not flag personal style preferences as findings.
4. Do not broaden review scope unless the current artifact cannot be evaluated without it.
5. If evidence is ambiguous, state the assumption or ask for clarification instead of declaring a defect.
6. Do not propose speculative flexibility or future-facing artifacts as review fixes.
7. Every recommendation should be verifiable by a schema edit, review pass, or test.

## Review Passes

Run these passes in order.

### Pass 1: Structural Validity

Check:

1. All ids use `snake_case`.
2. Every referenced id exists.
3. `high_level_flow` ids referenced by `runtime_flow` exist.
4. `runtime` container ids referenced by flows, verticals, persistent shapes, containers, and deployment exist.
5. `data_shape` ids referenced by `persistent_shape` exist.
6. `runtime_flow` ids referenced by `container` exist.

Escalate immediately if the schema cannot be crawled reliably.

### Pass 2: Stage Discipline

Check:

1. `high_level_flow` stays business-level.
2. `runtime_flow` stays container-level.
3. `container` stays component-level.
4. `early_state` has not become a hidden type system.
5. `deployment` has not become infra-as-code detail.

Flag any artifact that is operating at the wrong abstraction level.

### Pass 3: Flow Logic

Check:

1. A high-level flow uses only:
   - linear step: `next`
   - decision step: `branches`
   - terminal step: neither
2. A runtime-aware or component flow uses only:
   - linear step: `next` with optional `outgoing`
   - decision step: `branches`
   - terminal step: neither, or terminal `outgoing` for component-flow boundary output
3. No flow step mixes linear and branch forms.
4. Runtime-aware steps represent one container participation each.
5. Component-flow steps represent one component participation each.
6. `next` or branch targets may point to earlier steps when the loop is intentional.
7. A container may retain in-flight workflow-scoped state across its own runtime steps when it is clearly the orchestrator of the slice.
8. Do not assume that a later step only knows the immediately preceding boundary payload when the same container is plausibly coordinating the broader workflow.

For orchestrated runtime flows:

- Do not raise a contract-consistency finding solely because earlier workflow context is not re-threaded through every intermediate boundary hop.
- Do not require a new `persistent_shape` for intermediate context unless durability is actually needed.
- Raise a finding only when the artifact is ambiguous about whether the needed knowledge comes from:
  - immediate boundary payloads
  - retained in-flight workflow state
  - reloaded durable state

Accept explicit wording such as:

- "acts as the workflow orchestrator for this slice"
- "retains in-flight workflow context across its own steps"
- "correlates the payment intent with earlier challenge-entry context"
- "uses backend-retained workflow state established earlier in the flow"

### Pass 4: Promotion Discipline

Check:

1. One-off payloads are not promoted into `data_shape` without justification.
2. Reused or persisted important shapes are considered for promotion.
3. `persistent_shape` is used only for durable, architecturally significant state.
4. `container` exists only where a runtime container truly needs internal modeling.
5. A vertical is treated as a build slice rather than a vague capability bucket.

Use these challenge questions:

- Why is this not inline?
- Why does this need a stable name?
- Is this actually persisted?
- Does this container really need internal component modeling?
- Is this vertical really buildable end to end?

Require a new `persistent_shape` only when the intermediate state must be durable for:

- retry after interruption
- recovery after process loss
- auditability
- reconciliation
- cross-session continuation
- asynchronous resumption that cannot rely on live in-flight state alone

### Pass 5: Security Coverage

Check:

1. `system.security` exists when system-wide security rules clearly matter.
2. `runtime.containers[].security` exists where container-specific obligations matter.
3. `persistent_shapes[].security` exists where stored-data protections matter.
4. `deployment` trust boundaries align with the stated security story.
5. Sensitive persisted shapes are not modeled without corresponding protection expectations.

### Pass 6: Runtime and Deployment Coherence

Check:

1. Runtime and deployment describe the same architecture.
2. Integral external services are modeled consistently as `external_container` where appropriate.
3. Deployment nodes place the expected runtime containers.
4. Trust boundaries make sense relative to node kind and role.
5. Deployment notes add architectural signal rather than operational noise.

## Anti-Bloat Review Rules

Review should be aggressive about over-modeling.

Flag these patterns:

1. A `data_shape` exists for a clearly one-off payload.
2. A `persistent_shape` exists for something transient.
3. A container exists for a conceptual role rather than a real runtime boundary.
4. A `container` artifact models classes, files, or framework internals rather than meaningful components.
5. A deployment node carries detail that belongs in infrastructure config rather than architecture.
6. A new artifact exists only because the schema permits it, not because the system needs it.

## Routing Rules

Route issues back to the right stage.

- unclear boundary, purpose, or top-level architecture -> `forge-schema` at `system` or `runtime`
- unclear or invalid vertical definition -> `forge-schema` at `vertical`
- broken flow logic -> `forge-schema` at `high_level_flow` or `runtime_flow`
- bad promotion decisions -> `forge-schema` at `data_shape` or `persistent_shape`
- overgrown internals -> `forge-schema` at `container`
- deployment drift -> `forge-schema` at `deployment`
- security-specific gaps -> `forge-security`
- implementation sequencing or build-slice execution problems -> `forge-build`

## Constraints

1. Findings are the primary output.
2. Do not silently author missing architecture in review.
3. Do not accept bloat just because it is structurally valid.
4. Prefer a short, sharp findings list over a long descriptive recap.
