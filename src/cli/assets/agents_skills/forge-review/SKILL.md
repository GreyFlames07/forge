---
name: forge-review
description: >
  Forge V2 review skill. Use when a schema scope or implementation slice is ready for review and the
  user wants findings on completeness, consistency, contracts, security posture, bootstrap fragility,
  and verification quality before or during build. Produces forge/workbench/review.md and applies no
  schema edits without human approval.
---

# forge-review

Read before starting:

- `docs/forge-v2-schema.md`
- `docs/forge-v2-architecture.md`
- `frameworks/review/FRAMEWORK.md`
- `forge/workbench/discovery.md`
- current files under `forge/`

## Purpose

Challenge the schema and implementation before drift hardens.

This stage proposes edits and findings. It does not invent new schema objects without routing back to the proper authoring stage.

## Security Posture Interview

Required first step for a meaningful review.

Ask the human:

1. Who are you worried about? (external attackers, insider threats, compromised services, operator mistakes, none yet)
2. What is the most sensitive data or action in this system?
3. Any compliance or governance requirements?
4. What auth posture should be assumed by default?
5. What surfaces are actually exposed?

Record the answers at the top of `forge/workbench/review.md`.

## Review Passes

Run all passes. Collect findings before presenting them.

### Pass 1 — Completeness

Check:

- bootstrap exists and is concrete
- units referenced by bootstrap exist
- operations have inputs, outputs, referenced types, and error contracts where required
- surfaces reference real operations
- flows reference real surfaces, operations, or units
- verification exists for startup, bootstrap, and critical flows
- build policy actually reflects the stated philosophy

Structural validation errors are always top-severity findings.

### Pass 2 — Consistency

Check:

- every referenced type, operation, surface, store, flow, unit, and vertical exists
- auth contexts referenced in operations and surfaces exist in `system.auth_contexts`
- persistence semantics align with store usage
- lifecycle states and transitions align with operations
- workbench artifacts do not imply a plan the schema cannot support

### Pass 3 — Contract Correctness

Check:

- public and cross-unit operations use canonical named types
- operations with multiple contract types declare them explicitly instead of collapsing them into one payload
- surfaces do not redefine independent contracts unnecessarily
- error mappings are coherent
- event behavior uses named event types
- field `spec` strings are specific enough to constrain implementation

### Pass 4 — Access Control and Security Posture

Using the stated posture as the benchmark, check:

- mutating operations have appropriate auth context
- sensitive or restricted data is classified
- approval-gated behavior is explicit where required
- public surfaces do not bypass declared auth assumptions
- operator-only paths are clearly distinguished

### Pass 5 — Attack Surface and Failure Semantics

Apply only relevant vectors, not a rote checklist:

- injection risks
- SSRF-style outbound risks
- broken access control
- replay/idempotency gaps
- unsafe state transitions
- missing rate controls or retries where needed
- bootstrap fragility under partial failure

### Pass 6 — Verification Fitness

Check:

- can bootstrap actually be proved from the declared verification items?
- are operator checks present where automation is weak?
- are critical flows verifiable or only described?
- does the plan rely on checks the schema never declared?

## Output Format

Write `forge/workbench/review.md` with:

- security posture summary
- findings by severity
- proposed fixes
- explicit routes back to `forge-discover`, `forge-spec`, `forge-plan`, or `forge-build` where needed

## Failure Routing

- If the main issue is unclear system shape or unstable boundaries, route back to `forge-discover`.
- If the review finds missing or drifting contracts, route back to `forge-spec`.
- If the review finds ordering or slice-definition issues, route back to `forge-plan`.
- If the review finds a broken runnable path, route immediately to `forge-build` with bootstrap repair as the first priority.

## Approval Flow

1. present findings first
2. group by severity
3. show any proposed schema edits as before/after snippets
4. ask for approval before applying them

## Key Constraints

- Never silently edit schema files.
- Never create new nodes in review; route to the right authoring stage if needed.
- Findings are the primary output.
