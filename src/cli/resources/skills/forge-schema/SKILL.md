---
name: forge-schema
description: >-
  Build and refine the Forge V2 schema framework through a guided workshop.
  Use when defining or updating the canonical Forge V2 architecture artifacts:
  system, high-level flows, early state, runtime, verticals, runtime flows,
  data shapes, persistent shapes, containers, and deployment. Use when the
  user wants consultation rather than blind drafting, when artifact bloat must
  be controlled, or when a whole-system model must be turned into one vertical
  at a time.
---

# forge-schema

Read before starting:

- `../../SCHEMA_REFERENCE_V3.md`

Maintain throughout the workflow:

- `../../decision_notes.md`

## Purpose

Drive the Forge V2 schema process as a workshop, not an autonomous drafting pass.

This skill should:

1. Build the whole system model at a high level first.
2. Stop after `runtime` and derive the initial `verticals`.
3. Choose one vertical to deepen.
4. Build the lower-stage artifacts for that vertical.
5. Apply anti-bloat and review gates continuously.
6. Record every meaningful modeling decision in `decision_notes.md`.

Do not jump ahead. Do not define later-stage artifacts before the earlier stage is stable enough to justify them.

## Working Style

Follow these rules throughout:

1. Consult the user before locking in structure.
2. Ask only the questions needed to resolve the current stage.
3. Push back on unnecessary artifacts, types, and abstractions.
4. Prefer inline payload definitions until promotion is justified.
5. Keep every artifact tied to a real architectural or build need.
6. Infer from existing artifacts before asking the user to restate information.
7. Ask questions in small 3-5 question batches, not long questionnaires.
8. Ask follow-up questions only when ambiguity blocks the next drafting step.
9. Log every meaningful decision as soon as it is made.

## Decision Notes Rule

Maintain a markdown file named:

- `decision_notes.md`

This file should clearly record every meaningful decision made during schema development.

Record:

- the decision
- the stage where it was made
- the reasoning behind it
- any important alternatives that were rejected
- any assumptions that still remain open

Update `decision_notes.md` whenever:

- a boundary is fixed
- a flow structure is chosen
- a container is introduced or rejected
- a vertical is chosen or reordered
- a payload is promoted or intentionally kept inline
- a persisted shape is introduced
- a container artifact is justified
- a deployment assumption is fixed
- a security obligation is made explicit

Do not leave decisions only in chat if they materially affect the framework.

## Questioning Protocol

Apply this protocol at every stage.

1. Read the existing artifacts for the current scope first.
2. Infer everything that is reasonably supported by the existing material.
3. Ask only for information that cannot be safely inferred.
4. Ask the highest-yield questions first.
5. Ask questions in batches of closely related items.
6. If ambiguity remains after the answer, ask a narrow follow-up question instead of restarting the stage.

### High-Yield Question Standard

Prefer questions that unlock multiple downstream decisions at once.

Good examples:

- What is the first end-to-end slice you want working?
- Which high-level flows belong to that slice?
- What runtime boundaries are real versus merely conceptual?

Avoid low-yield questions that only rename things or ask for details that can be inferred from already-stated context.

## Draft-First Rule

Use a draft-first approach for the deeper stages where structure is easier to critique than to invent from scratch.

Apply this especially to:

- `vertical`
- `runtime_flow`
- `container`
- `deployment`

Draft-first means:

1. Build a lean first draft from the current evidence.
2. State the key logic behind the draft.
3. Ask the user to critique the draft rather than answer from a blank page.
4. Revise based on critique.

When using draft-first mode:

- explain why the draft is structured that way
- call out assumptions explicitly
- keep the first draft minimal
- do not overfill optional fields just because the schema permits them

## Workflow

### Phase 1: Whole-System Framing

Complete these stages in order:

1. `system`
2. `high_level_flow`
3. `early_state`
4. `runtime`

For each stage:

1. Read the matching section in `SCHEMA_REFERENCE_V3.md`.
2. Summarize what the stage is trying to define.
3. Ask targeted questions.
4. Draft or refine the artifact.
5. Run the review gate for that stage before moving on.

### Phase 2: Vertical Initialization

After `runtime` is stable:

1. Derive candidate `verticals`.
2. Explain that a vertical is a development slice, not a business domain.
3. Draft the initial `verticals` artifact even if some fields stay empty.
4. Explain the logic behind the proposed vertical boundaries.
5. Ask the user to critique the draft and choose the first vertical to deepen.

Do not define `runtime_flow`, `data_shape`, `persistent_shape`, `container`, or `deployment` for the whole system at once unless the user explicitly wants that. Default to one vertical at a time.

### Phase 3: Vertical Deepening

For the selected vertical, complete these stages in order:

1. `runtime_flow`
2. `data_shape`
3. `persistent_shape`
4. `container`
5. `deployment`

For each stage:

1. Ask only the questions needed for the chosen vertical.
2. Keep one-off details inline unless promotion is justified.
3. Use draft-first mode when the structure is easier to critique than invent.
3. Run the review gate before moving on.

## Stage Questions

Use these as the default interview prompts. Ask only the subset needed for the current scope.

### `system`

- What is the system trying to do?
- What is inside the boundary?
- Who interacts with it?
- Which external dependencies matter at system context level?
- What global security rules are non-negotiable?

### `high_level_flow`

- What can the user or system actually do?
- What starts the flow?
- What are the major business steps?
- Where do business decisions happen?
- What are the canonical outcomes?

### `early_state`

- What business things matter enough to name now?
- Which are entities, records, or lifecycle objects?
- Why does each one matter?

### `runtime`

- What actually runs?
- What actually persists?
- Which real runtime boundaries exist?
- Which containers relate to each other?
- What security obligations belong to each container?

### `vertical`

- What is the first buildable end-to-end slice?
- What user value does it deliver?
- Which high-level flows belong to it?
- Which runtime containers are involved?
- What deployment or build constraints matter already?

Default behavior:
- Draft 1-3 likely verticals from the current system model.
- Explain why each is a real build slice.
- Ask the user which draft to refine, merge, reject, or reorder.

### `runtime_flow`

- How does the selected vertical move through containers?
- What exact payload enters the first container?
- What exact payload leaves each container?
- Where do branches occur?
- Which outputs are one-off and which feel reusable?

### `data_shape`

- Which payloads or stored shapes are reused?
- Which are persisted?
- Which are important enough to deserve a stable named definition?
- Which should stay inline instead?

### `persistent_shape`

- Which shapes are actually persisted?
- Which container logically owns each persisted shape?
- Which data store container holds it?
- What storage model applies?
- What lifecycle, security, and state-machine behavior matters?

### `container`

- Which container actually needs internal modeling?
- What meaningful components exist inside it?
- How does the chosen runtime flow move between those components?
- Should internal logic stay in a step description rather than becoming another artifact?

Default behavior:
- Draft a minimal component partition first.
- Explain the reasoning for each component boundary.
- Ask the user to critique the partition before expanding the flow.

### `deployment`

- Which environments matter?
- Which nodes exist in those environments?
- Which containers run on which nodes?
- What deployment notes matter: technology, endpoint, region, scaling, availability, dependencies, trust boundary?

## Anti-Bloat Rules

Apply these rules aggressively.

### Global Rules

1. Do not create an artifact unless it answers a real architectural or build question.
2. Do not create a later-stage artifact before the earlier stage justifies it.
3. Prefer plain-language fields over structure when the detail does not need machine semantics.
4. Prefer one stable artifact shape over multiple near-duplicate artifact types.
5. Prefer draft-and-critique over speculative completeness in the deeper stages.
6. Do not ask the user for information that is already present in the artifacts or can be inferred reliably.

### Stage-Specific Rules

`system`
- Keep the boundary plain-language.
- Do not introduce policies, invariants, or compliance structure unless they are clearly system-defining.

`high_level_flow`
- Keep it business-level.
- Do not mention containers, protocols, schemas, or internal implementation here.
- Keep decisions inside `steps`, not as a parallel artifact.

`early_state`
- Keep it lightweight.
- Do not turn it into a type system.
- Do not define exact fields, persistence models, or detailed state machines here.

`runtime`
- Create a container only if it is a real application, data store, or runtime boundary.
- Do not create conceptual containers for vague responsibilities.
- Do not confuse code organization units with containers.

`vertical`
- Treat a vertical as a build slice, not a business capability bucket.
- Do not define a vertical only because a concept exists; it must describe an end-to-end slice that could be built.
- Initialize the full vertical schema shape, but allow empty fields until later stages justify filling them.

`runtime_flow`
- Use one step per container participation in the flow.
- Do not model internal execution inside the container here.
- Keep payloads inline by default.
- Promote nothing at this stage just for elegance.
- Draft the first flow path from the known runtime and high-level flow before asking the user to invent it from scratch.

`data_shape`
- Promote only when data is reused, persisted, or otherwise important enough to require a stable named definition.
- Keep one-off payloads inline in the flow.
- Do not create shapes merely because a payload exists.

`persistent_shape`
- Create one only for durably stored, architecturally significant state.
- Every persistent shape must reference a real `data_shape`.
- Do not create persistent shapes for transient requests or responses.

`container`
- Create this only for containers that truly need internal modeling.
- Model flows between components, not between classes or files.
- Prefer a stepped `description` inside a component step over creating more flow artifacts.
- Do not let this collapse into code-level noise.
- Draft a minimal component decomposition first and require critique before elaboration.

`deployment`
- Keep this architecture-level.
- Include deployment notes that matter, but do not drift into raw IaC detail, resource sizing minutiae, or vendor config dumps.

## Review Rules

Run these checks before leaving each stage and again at the end of the skill.

### Structural Checks

1. All ids use `snake_case`.
2. Every referenced id exists.
3. Every flow references the correct prior-stage artifact ids.
4. Every `persistent_shape.data_shape` points to a real `data_shape`.
5. Every runtime/deployment container reference points to a real runtime container.
6. Every draft-first stage includes explicit assumptions or rationale for the initial draft.

### Flow Checks

1. `high_level_flow` stays business-level.
2. `runtime_flow` uses container-level steps only.
3. `container` uses component-level steps only.
4. A flow step is either:
   - linear: `next` plus `outgoing`
   - decision: `branches`
   - terminal: neither
5. Reject steps that mix linear and branch forms.

### Promotion Checks

1. Challenge every proposed `data_shape` with: "Why is this not inline?"
2. Reject promoted shapes that are one-off and non-persistent unless the user explicitly wants the stable reference.
3. Challenge every proposed `persistent_shape` with: "Is this actually durable state?"
4. Challenge every proposed `container` artifact with: "Does this container really need internal component modeling?"
5. Challenge every proposed question with: "Can this be inferred instead?"

### Security Checks

1. `system.security` exists when system-wide rules matter.
2. `runtime.containers[].security` exists where container-specific obligations matter.
3. `persistent_shapes[].security` exists where stored-data protections matter.
4. `deployment` trust boundaries align with the security story.

### Consistency Checks

1. Repeated payloads that are clearly reused or persisted are considered for promotion.
2. One-off payloads remain inline.
3. External integral services are modeled consistently as `external_container` when they are part of the runtime model.
4. Deployment examples and runtime examples describe the same architecture, not competing ones.
5. The skill asks in batches and uses follow-up questions only to resolve blocking ambiguity.

## Completion Criteria

For a whole-system pass:

- `system`, `high_level_flow`, `early_state`, `runtime`, and `vertical` are stable enough to choose a first vertical.

For a vertical-deepening pass:

- The selected vertical has a coherent `runtime_flow`.
- Promoted `data_shape`s are justified.
- Real durable state is captured in `persistent_shape`.
- Any `container` artifact is justified and readable.
- `deployment` reflects the selected vertical at the right abstraction level.

## Failure Routing

- If the user is still clarifying purpose and boundary, stay in `system`.
- If flows remain conceptually unclear, do not move into runtime.
- If runtime boundaries are unclear, do not initialize verticals yet.
- If a proposed artifact feels decorative, challenge it before drafting it.
- If the user wants a final coherence pass instead of more authoring, route to `forge-review`.
- If the user wants a security-focused pass, route to `forge-security`.
- If the user wants implementation sequencing or vertical delivery execution after runtime or vertical definition, route to `forge-build`.
