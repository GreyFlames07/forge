---
name: forge-discover
description: >
  Forge V2 discovery skill. Use when a user is starting a new system, reshaping an existing
  system, or needs the top-level V2 foundation drafted from an interview. Drives an agent-led,
  value-focused interview that produces the initial Forge V2 schema skeleton: system, verticals,
  units, bootstrap, build policy, and workbench discovery notes. Triggers on: "start a new forge
  project", "design a new system", "workshop this idea", "forge-discover", or any request to
  begin Forge V2 work from a vague or partially formed idea.
---

# forge-discover

Read before starting:

- `docs/forge-v2-schema.md`
- `docs/forge-v2-architecture.md`
- `frameworks/discover/FRAMEWORK.md`

## Purpose

Drive a focused interview that takes a human from a vague product idea to a concrete V2 foundation.

This stage is about:

- what the system is for
- what value it must deliver first
- what profile it is
- what verticals matter first
- what runtime units must exist
- what the bootstrap path is
- what global constraints must shape every later stage

The interview is not generic brainstorming. Every question must directly shape one or more V2 schema nodes.

## Output Artifacts

| File | Contents |
|------|----------|
| `forge/system.yaml` | System identity, purpose, goals, auth contexts, security posture, environments |
| `forge/verticals/*.yaml` | One file per initial business capability slice |
| `forge/units/*.yaml` | One file per required runtime unit |
| `forge/bootstrap.yaml` | The first runnable vertical slice |
| `forge/build_policy.yaml` | Bootstrap-preserving build rules |
| `forge/workbench/discovery.md` | Living rationale and deferred decisions for downstream stages |

## Interview Standard

### Non-negotiables

1. Ask only high-yield questions. If a question does not affect schema shape, bootstrap shape, or repo scaffolding, do not ask it.
2. Batch within phases; do not blend phases.
3. Critical architectural choices get option sets with tradeoffs, not silent defaults.
4. Do not ask implementation-detail questions that belong in `forge-spec`.
5. Draft only after the bootstrap path is clear enough to be meaningful.
6. `forge/workbench/discovery.md` is a first-class artifact. Capture the reasoning, not just the decision.

## Interview Phases

Work through phases in order. Ground each question in prior answers.

### Phase 1 — System Intent

Establish:

- what the system does
- who benefits from it
- what outcome must work first
- what is explicitly out of scope
- what the system must never get wrong

Seed questions:

- What does this system do in one clear statement?
- Who benefits from it, and what can they accomplish through it?
- What is the smallest useful outcome that should work first?
- What is explicitly out of scope for this system?
- What is the one thing it absolutely must get right?

Do not move on until the scope boundary and first-value outcome are clear.

### Phase 2 — Project Profile and Bootstrap Shape

Establish:

- project profile
- bootstrap interaction mode
- whether the first runnable slice is web, API, CLI, worker, or mixed

Present profile options with tradeoffs when needed:

- `full-stack`
- `api-service`
- `cli-tool`
- `worker-service`

Questions:

- Which project profile best fits this system?
- What does the bootstrap path actually look like from the operator or user point of view?
- Does bootstrap require a user-facing app, an API, a CLI command, a background trigger, or a combination?
- What would count as "it works" for the first runnable slice?

### Phase 3 — Verticals

Establish:

- the first business capability slices
- what each vertical owns
- what each vertical explicitly does not own

Questions:

- What are the first 2–5 business capabilities this system needs?
- For each capability: what does it own exclusively?
- Where are the natural seams, where one capability can change without forcing another to change?
- Which vertical contains the bootstrap path?

Resist naming a vertical until its boundary is clear.

### Phase 4 — Runtime Units

Establish:

- the units that must exist for bootstrap and immediate expansion
- what each unit exposes or runs
- which units are independently promotable

Questions:

- What distinct runtime parts actually need to run?
- Which unit serves the bootstrap interaction?
- What does each unit own exclusively?
- Which units depend on which other units or stores?
- Can any of these be booted, deployed, or promoted independently?

One unit = one operational runtime boundary.

### Phase 5 — Global Constraints

Establish:

- auth contexts
- security posture
- promotion stages
- environments

Questions:

- What caller contexts exist? (anonymous user, session user, service identity, operator, etc.)
- What global security or approval rules are non-negotiable?
- What environments and promotion stages matter?
- Are there operator checks that bootstrap will require because the system cannot be fully machine-verified?

### Phase 6 — Platform Sketch

Keep this general at discovery stage.

Questions:

- What platform or hosting direction is expected?
- What primary language or stack direction is expected?
- Are there obvious infrastructure constraints that later stages must respect?

Do not ask for concrete datastore engines, file structures, or payload fields here.

## Assembly

After the interview, before writing any files:

1. Restate all major decisions as a compact summary.
2. Ask for confirmation if any critical ambiguity remains.
3. Write the schema skeleton in one pass.
4. Populate `forge/workbench/discovery.md` with:
   - system intent
   - bootstrap definition
   - profile choice and why
   - vertical map
   - runtime unit map
   - security posture
   - open questions deferred to `forge-spec` or `forge-plan`

## Exit Condition

State:

> "Discovery is complete. We have the V2 foundation: system, verticals, units, bootstrap, build policy, and discovery notes. Ready to move to `forge-spec` for operations, contracts, stores, flows, and verification."

Wait for human confirmation before closing.

## Failure Routing

- If the first runnable outcome is still unclear, stay in `forge-discover`; do not draft speculative bootstrap files.
- If capability boundaries are still unstable, keep the work in `forge-discover`; do not force vertical or unit definitions early.
- If the human starts asking for operations, contracts, stores, or flow specifics, finish the discovery boundary first and then route forward to `forge-spec`.
- If bootstrap cannot be described concretely enough to scaffold, stop and surface the missing decision instead of inventing one.

## Key Constraints

- Do not create types, operations, surfaces, stores, flows, or verification items here.
- Do not invent units or verticals the human has not actually described.
- Bootstrap must be concrete enough to scaffold and run.
- `build_policy` must reflect bootstrap preservation and vertical-first delivery.
