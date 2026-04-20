# forge-compose — Framework

This document is the deeper mental model for `forge-compose`. The skill artifact
(`SKILL.md`) is optimized for execution. This file explains rationale, decision
gates, and consistency rules when composing L4 flows and journeys.

## 1. Purpose and position in the pipeline

`forge-compose` is the composition stage between atom elicitation and audit:

```
discover -> decompose -> atom -> compose -> audit -> armour -> implement -> validate
```

It takes completed atom contracts and produces L4 orchestration specs:

- `L4_flows/flow.*.yaml`
- `L4_journeys/jrn.*.yaml`

It does not create atoms, L0 entities, modules, or policies.

## 2. Inputs and prerequisites

Minimum prerequisites:

1. Relevant atoms exist and have complete specs in `L3_atoms/`.
2. Module entry points are present in `L2_modules/*.yaml`.
3. `discovery-notes.md` exists and is treated as canonical context.

Additional constraints (if present):

- `decision-log.md`
- `docs/decisions/*.md`
- `docs/adr/*.md`
- `implementation-plan.yaml` (`architecture` section)
- `security-profile.md`

Decision precedence for conflicts:

1. Human override in current session
2. Decision artifacts
3. Discovery notes
4. Inferred defaults from contracts/conventions

Silence is not consent for critical decisions.

## 3. Review depth and decision checkpoints

### C1 — Draft review

Use when orchestration is straightforward and low risk. Produce draft, collect
corrections, revise once.

### C2 — Draft + focused decisions (default)

Use when trigger, boundary, retry, compensation, idempotency, or exits are not
fully implied by existing specs.

### C3 — Draft + critical challenge

Use for financial/auth/compliance/high-concurrency paths or any flow with
material partial-failure impact.

Critical decision checkpoints:

1. Trigger source and contract
2. Transaction boundary (`acid` | `saga` | `none`)
3. Retry semantics (conditions, attempts, backoff)
4. Compensation model per step
5. Idempotency key source/window
6. Exit-state and failure semantics
7. Cross-module orchestration ownership

## 4. Required composition checks

Before writing or approving a flow/journey:

1. Every `invoke` target resolves and contract shapes align.
2. Retry paths include idempotency strategy where side effects exist.
3. Saga compensation is explicit (or explicitly non-compensable).
4. Journey transitions are total for non-terminal states.
5. L2 entry points align with L4 trigger definitions.
6. L1/L5 constraints are not contradicted by orchestration behavior.
7. Decision artifacts are not violated by the proposed draft.

Contradictions are surfaced as option sets; never silently resolved.

## 5. Contradiction probes

Common contradiction classes:

- **Boundary mismatch:** current decision docs require `saga`, draft uses `acid`.
- **Retry/idempotency mismatch:** retry added without key source.
- **Compensation gap:** side-effect step in saga has no compensation route.
- **Entry-point drift:** L2 entry invokes a different flow than the draft.
- **Exit drift:** journey terminal state semantics conflict with discovery notes.

Escalation rule:

- One contradiction -> present compact option set.
- Multiple linked contradictions -> pause and resolve boundary model first.

## 6. Artifacts and write-back

`forge-compose` writes three artifact classes:

1. **L4 specs:** flow/journey files plus changelog entries.
2. **Discovery updates:** composed status + orchestration notes + unresolved
   tensions in `open_questions`.
3. **Decision updates:** append critical composition decisions to decision docs.
   If no decision doc exists, initialize `decision-log.md`.

Decision log entry shape:

```md
## <YYYY-MM-DD> - <flow_or_journey_id>
- decision: <short title>
- options_considered: [<a>, <b>, <c>]
- chosen: <option>
- rationale: <1-3 lines>
- impacts:
  - <spec files>
  - <runtime/ops implication>
```

## 7. Handover and routing

When composition is complete for the current scope:

- If more L4 units remain -> route to next `/forge-compose <id>`.
- If scope complete -> route to `/forge-audit`.

When blocked:

- Missing/partial atom contracts -> route to `/forge-atom`.
- Module boundary ambiguity created by missing atom ownership -> route to
  `/forge-decompose` for module-level correction, then return.

## 8. What forge-compose does NOT do

- Does not create new atoms or atom spec blocks.
- Does not create L0 types/errors/constants.
- Does not create modules.
- Does not create policies.
- Does not implement code or tests.

Its sole responsibility is composition contracts in L4 plus related decision
traceability.
