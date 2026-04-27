# forge-compose — Framework

This is the human-facing mental model for `forge-compose`: the composition
skill that turns completed atom contracts into L4 flows and journeys while
respecting discovery context and project decision records.

## 1. Purpose and position in the pipeline

`forge-compose` sits between atom elicitation and spec audit:

```
discover -> decompose -> atom -> compose -> audit -> armour -> implement -> validate
```

Outputs:

- `L4_flows/flow.*.yaml`
- `L4_journeys/jrn.*.yaml`

Non-goals:

- no new atoms
- no L0 creation
- no module or policy creation
- no code implementation

## 2. Required inputs

Composition starts from contracted atoms and project context:

1. `L3_atoms/*.yaml` (complete enough to compose)
2. `L2_modules/*.yaml` entry points
3. `supporting-docs/discovery-notes.md` (authoritative context)

If present, these are treated as constraints:

- `supporting-docs/decision-log.md`
- `docs/decisions/*.md`
- `docs/adr/*.md`
- `supporting-docs/implementation-plan.yaml` architecture block
- `supporting-docs/security-profile.md`

Priority when signals conflict:

1. Explicit human choice in-session
2. Existing decision artifacts
3. Discovery notes
4. Inferred defaults

## 3. Decision depth model

### C1 — Draft review

Low-risk orchestration. Draft first, collect corrections, revise once.

### C2 — Draft + focused decisions (default)

Used when trigger/boundary/retry/compensation/idempotency/exits are not fully
determined from existing contracts and docs.

### C3 — Draft + critical challenge

Used for high-risk paths (financial, auth, compliance, high concurrency, or
multi-side-effect failure risk).

Critical checkpoints:

1. Trigger source and payload contract
2. Transaction boundary (`acid` / `saga` / `none`)
3. Retry semantics
4. Compensation semantics
5. Idempotency source and dedupe window
6. Exit/failure semantics
7. Cross-module orchestration ownership

## 4. Consistency gates before write

Before accepting an L4 draft:

1. Every `invoke` reference resolves and contract mapping is valid.
2. Retry paths with side effects have idempotency strategy.
3. Saga steps are compensable or explicitly exempted.
4. Journey transitions are total for all non-terminal states.
5. L2 entry points and L4 triggers align.
6. L1/L5 constraints are honored.
7. Decision artifacts are not contradicted.

Contradictions are surfaced as option sets, never silently resolved.

## 5. Artifact updates

`forge-compose` writes:

1. L4 spec files + changelog entries.
2. `supporting-docs/discovery-notes.md` updates (status, notes, unresolved tensions).
3. Decision log updates for critical composition choices.

If no decision log exists, create `<spec-dir>/supporting-docs/decision-log.md`.

Recommended decision entry:

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

## 6. Handover routing

- More L4 units left: continue `/forge-compose <next_id>`.
- L4 scope complete: run `/forge-audit`.
- Missing atom contracts: return to `/forge-atom`.
- Module-ownership ambiguity: resolve via `/forge-decompose`, then resume compose.

## 7. Boundaries

`forge-compose` is a composition skill, not a creator of lower-layer entities.
Its core value is drafting orchestration first, then extracting only the
critical decisions that cannot be safely inferred.
