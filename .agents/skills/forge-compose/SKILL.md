---
name: forge-compose
description: >
  Use this skill when the user needs to compose completed L3 atoms into L4
  orchestration specs - flows and journeys. Activates on phrases like
  "compose flows", "build journeys", "wire atoms into workflows", "create L4",
  "draft flow X", or when L3 atoms are mostly complete but L4_flows/ and
  L4_journeys/ are empty or partial. Starts with inferred drafts from atom
  contracts, module entry points, L1/L5 conventions, supporting-docs/discovery-notes.md, and
  decision docs (decision log / ADRs / architecture decisions), then asks only
  unresolved decision questions (trigger, transaction boundary, retry,
  compensation, idempotency, exits). Produces or updates L4 flow/journey files,
  updates discovery and decision artifacts, and appends changelogs. Does NOT
  create atoms, L0 entities, modules, or policies.
---

# forge-compose

Compose implementation-ready L4 flows and journeys from already-elicited atoms. Work draft-first: infer a plausible orchestration from the current specs and project decisions, present it, then ask only the decision questions the draft cannot settle safely.

Full mental model is in `references/framework.md`. Load on demand:
- `§3` for review depth and decision checkpoint guidance
- `§4` for required flow/journey shape checks
- `§5` for contradiction probes and escalation
- `§7` for handover and routing rules

This file is self-sufficient for routine operation.

## Non-negotiables

1. **Draft first; question second.** Always produce a best-effort draft before broad elicitation.
2. **Decision-only questioning.** Ask only where multiple valid orchestration choices exist.
3. **Composition scope only.** Never create atoms, L0 types/errors/constants, modules, or policies.
4. **Discovery doc is mandatory context.** Read `<spec-dir>/supporting-docs/discovery-notes.md` before drafting.
5. **Decision docs are binding constraints.** If present, decision log/ADRs/architecture constraints must be honored unless explicitly revised by the human.
6. **Critical decisions get option sets.** For boundary/retry/compensation/idempotency/exit semantics, present 2-4 options when ambiguous.
7. **Retry requires idempotency.** No retry policy without an explicit key source.
8. **Saga requires compensation clarity.** Each compensable step needs compensation action or explicit non-compensable rationale.
9. **No silent contradictions.** If atom contracts conflict with orchestration, surface the exact entities and ask.
10. **Partial specs resume, not rewrite.** Confirm existing authored fields; revise only uncertain ones.
11. **Record critical composition decisions.** Write confirmed decisions back into discovery + decision artifacts.

## Workflow

### Step 1 - Load context and constraints

Run:

```bash
forge list --spec-dir <spec-dir>
forge inspect <target_or_module> --spec-dir <spec-dir>
forge context <target_or_seed_entity> --spec-dir <spec-dir>
```

Read in this order:

1. `<spec-dir>/supporting-docs/discovery-notes.md`
2. Decision artifacts (if present), priority order:
   - `<spec-dir>/supporting-docs/decision-log.md`
   - `<spec-dir>/docs/decisions/*.md`
   - `<spec-dir>/docs/adr/*.md`
   - `<spec-dir>/supporting-docs/implementation-plan.yaml` (`architecture` block)
   - `<spec-dir>/supporting-docs/security-profile.md`
3. Relevant L2/L3/L4/L1/L5 spec context from forge CLI output

If decision artifacts conflict with each other, present one compact option-set and resolve before drafting.

### Step 2 - Choose target and review depth

If invoked with an id (`flow.*` or `jrn.*`), use it.
If invoked without id, auto-pick highest leverage missing item:

1. First unresolved orchestration item in `supporting-docs/discovery-notes.md` `open_questions`
2. Entry-point-backed workflow with no L4 mapping
3. First missing flow, then first missing journey alphabetically

Depth selection:

| Condition | Depth |
|---|---|
| Low-risk, straight-through orchestration | **C1 - Draft review** |
| Ambiguous trigger/boundary/retry/exit choices | **C2 - Draft + focused decisions** |
| Financial/auth/compliance/high-concurrency critical path | **C3 - Draft + critical challenge** |

Default: **C2**.

### Step 3 - Draft first (sub-phase 1)

Produce a best-effort draft for the target flow/journey, then present:

1. Draft spec
2. Assumptions made
3. Decision points
4. Explicit conflicts
5. Discovery/decision-doc implications

#### C1 - Draft review

- Present draft
- Ask: *"What's wrong or missing?"*
- Revise once, then continue

#### C2 - Draft + focused decisions

Ask only unresolved checkpoints:

1. Trigger/entry mapping
2. Transaction boundary (`acid` / `saga` / `none`)
3. Retry policy (conditions, attempts, backoff)
4. Compensation policy
5. Idempotency key source/window
6. Exit semantics (success/terminal/recoverable)

Revise and present one compact second pass.

#### C3 - Draft + critical challenge

Run C2, then challenge:

1. Partial-failure ordering
2. Replay/duplicate delivery safety
3. Auth boundary transitions
4. Timeout/circuit-breaker behavior
5. User/operator-visible failure semantics

### Step 4 - Consistency probes (sub-phase 2)

Before writing, verify:

1. Every invoked atom/flow exists and contract is compatible
2. Retry paths have idempotency strategy
3. Saga compensation graph is coherent
4. Journey transitions are total (no dead non-terminal states)
5. L2 entry points and L4 trigger definitions align
6. L1/L5 conventions are not violated
7. Decision docs are not contradicted by new L4 behavior

Surface only contradictions; include exact ids/files and options.

### Step 5 - Write + update artifacts (sub-phase 3)

Write/update:

- `<spec-dir>/L4_flows/<flow_id>.yaml`
- `<spec-dir>/L4_journeys/<journey_id>.yaml` (if applicable)

Append changelog entries to touched L4 files.

Update discovery artifacts:

- `supporting-docs/discovery-notes.md`
  - mark composed items
  - add orchestration notes
  - add unresolved tensions to `open_questions`

Update decision artifacts:

- Append newly confirmed critical composition decisions:
  - boundary
  - retry + idempotency
  - compensation model
  - exit semantics
- If no decision doc exists, create `<spec-dir>/supporting-docs/decision-log.md` and append entries there.

Suggested decision-log entry format:

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

Validate:

```bash
forge context <flow_id> --spec-dir <spec-dir>
forge context <journey_id> --spec-dir <spec-dir>
```

If unresolved references remain, do not hand over as complete.

### Step 6 - Handover

If more items remain:

> *"`<id>` composed. Remaining: `<list>`. Next recommendation: `/forge-compose <next_id>`."*

If scope complete:

> *"L4 composition complete for `<scope>`. Next gate: `/forge-audit`."*

## Critical decisions - option-set protocol

Use option sets whenever unresolved:

1. Trigger source and contract
2. Transaction boundary
3. Retry policy and backoff
4. Compensation strategy
5. Idempotency key source/window
6. Exit states and failure semantics
7. Cross-module ownership of orchestration responsibility

Do not treat silence as agreement.

## What forge-compose does NOT produce

| Not produced | Deferred to |
|---|---|
| New atoms / atom spec blocks | `forge-decompose` + `forge-atom` |
| L0 types/errors/constants | `forge-atom` |
| New modules | `forge-discover` |
| New policies | policy flow/manual policy authoring |
| Implementation code/tests | `forge-implement` |

## Suggested skeletons

### Flow

```yaml
flow:
  id: flow.<name>
  transaction_boundary: <acid|saga|none>
  trigger:
    kind: <api|event|schedule|manual>
    source: <entry_or_event>
    request_type: <type_or_null>
  sequence:
    - step: 1
      invoke: atm.<mod>.<verb>
      on_error: <FAIL|RETRY(max=3,backoff=exp)|COMPENSATE>
    - step: 2
      invoke: atm.<mod>.<verb>
      compensation: atm.<mod>.<undo_verb>
  exits:
    success: <state_or_payload>
    failure: <state_or_error_contract>
  verification_criteria: []
  changelog: []
```

### Journey

```yaml
journey:
  id: jrn.<name>
  start: <state>
  handlers:
    - state: <state>
      atom: atm.<mod>.<component_or_proc>
  transitions:
    - from: <state>
      on: <event_or_action>
      to: <state>
      invoke: <optional flow.<name> or atom>
  exit_states:
    success: [<state>]
    failure: [<state>]
    abandoned: [<state>]
  verification_criteria: []
  changelog: []
```

## forge CLI commands used by this skill

| Command | Used for |
|---|---|
| `forge list --spec-dir <dir>` | scope/progress discovery |
| `forge inspect <id> --spec-dir <dir>` | load module/flow/journey shape |
| `forge context <id> --spec-dir <dir>` | compatibility + closure validation |
| `forge find <q> --kind atom --spec-dir <dir>` | candidate/invocation lookup |

## Gotchas

- Don't add retries without idempotency.
- Don't use saga compensation patterns under `acid` unless explicitly justified.
- Don't encode implementation details in L4 specs.
- If required atom contracts are incomplete, route back to `forge-atom` first.
- Keep discovery and decision docs synchronized with final L4 decisions.
