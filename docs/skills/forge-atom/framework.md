# forge-atom — Framework

This document describes the **mental model** for `forge-atom`: the stages, the draft-first review model, the three review depths, the consistency probes, the anti-bloat protocol, and the artifact cascades produced. It is **not** the SKILL.md; it is the source of truth from which any skill artifact is authored.

Audiences:
- An LLM or agent that executes the process
- An engineer authoring the `SKILL.md` from this framework
- A human facilitator running elicitation without an AI

---

## 1. What `forge-atom` is

**Purpose.** Take one atom stub produced by `forge-decompose` (id + kind + owner_module + description + empty `spec`) and produce a **complete, implementation-ready L3 atom spec** — the full `spec` block per kind, verification meeting L1 floors, and every cascade the atom forces: L0 writes (types, errors, constants), module-field completions (`persistence_schema.datastores`, `access_permissions`, filled `interface.entry_points`).

The workhorse skill. Run dozens to hundreds of times per project. The specs it produces drive implementation.

**Scope contrast:**

| | discover | decompose | **forge-atom** |
|---|---|---|---|
| Scope | Whole system | One module at a time | **One atom, with cascades** |
| Work type | Creative / exploratory | Analytical / extractive | **Contract-level / precise** |
| Kind sensitivity | No kinds yet | Same flow all kinds | **Four distinct spec shapes** |
| Interview feel | Workshop | Depth interrogation | **Draft review + contract challenge** |
| Duration | 1–2 hours total | ~10–15 min / module | **~5–40 min / atom (depth-dependent)** |
| Stakes | Framing | Revisable classification | **Specs drive implementation** |
| L0 writes | Skeleton only | None | **Types, errors, constants** |

**Outputs at exit:**

| Artifact | What |
|---|---|
| `L3_atoms/<atom>.yaml` | Complete spec — `spec` block populated per kind, verification meeting L1 floors |
| `L0_registry.yaml` | New types appended; new errors appended (confirmed); constants appended (with skepticism flag if single-consumer) |
| `L2_modules/<owner>.yaml` | `persistence_schema.datastores` updated; `access_permissions` extended; `interface.entry_points` stub completed |
| `discovery-notes.md` | Atom marked `status: elicited`; any new `open_questions` added |

---

## 2. Operating principles

Inherits everything from discover and decompose (one concept per turn, confirm by restating, extractive not generative, critical decisions get option sets, advisory anti-bloat probes, etc.).

**Principles specific to forge-atom:**

1. **Draft first; question second.** If a plausible spec can be inferred from the stub, siblings, owner module, L0/L1/L4 context, or discovery notes, the agent drafts before asking broad elicitation questions.
2. **Review depth matches criticality, not atom count.** Routine atoms get light review. Critical atoms get deeper challenge over business correctness, security, data integrity, external failure handling, and caller expectations.
3. **Input and output questioning is ambiguity-gated.** The agent drafts contracts by default, then opens explicit contract questions only when ambiguity or risk remains. The human should not be asked to enumerate fields from scratch when the draft is already directionally correct.
4. **Logic is prose-first.** Human describes corrections in natural language; agent normalizes to `WHEN / LET / CALL / RETURN / EMIT / SET / TRY` DSL for review. The human never has to produce DSL directly.
5. **Verification emerges from draft + review.** Example cases surfaced during review ARE example_cases. Edge paths surfaced during review ARE edge_cases. Invariants upheld across the draft and corrections ARE property_assertions. L1 floors are met by construction, not by a separate "now let's write tests" phase.
6. **Consistency probes are targeted, not exhaustive.** When a contradiction surfaces, the agent names it specifically (policy / sibling / called-atom / etc.) and presents options. When nothing surfaces, the probes are invisible — no narration.
7. **Anti-bloat probes fire at every L0 create.** Before writing a new type / error / constant, run the relevant reuse scan via `forge find`. Present matches advisorily.
8. **Within-module chain mode.** Context stays warm across atoms in the same module — sibling patterns, shared types, the just-elicited siblings inform subsequent atoms. `/clear` happens between modules, not between atoms (unless human opts in).
9. **Stubs get filled; never recreated.** Partial spec handling is confirm+resume: show existing fields, allow corrections, then continue from the first unfilled or uncertain field. Never wipe and restart unless the human explicitly asks.
10. **Structured primitives are not allowed to stay implicit.** If a primitive field is parsed, split, pattern-matched, used as a discriminator, or structurally consumed by downstream logic, the review must either add a `shape` block or explicitly confirm the field is opaque pass-through. Bare primitive types are only acceptable for opaque tokens.

---

## 3. Review depth selection

The agent selects the review depth from the atom's surfaced criticality at sub-phase 0 exit. All depths start the same way: load context, draft the atom, present the draft, and ask only the questions the draft cannot settle. The selected depth controls how much challenge happens *after* the first draft is on the table.

### Selection rules

| Condition | Depth |
|---|---|
| Routine, sibling-pattern, low-risk atom | **D1 — Draft review** |
| Meaningful ambiguity, side effects with cross-entity implications, or likely L0/module cascades | **D2 — Draft + focused decisions** (default) |
| Critical to module purpose, business correctness, security, data integrity, or `kind: MODEL` | **D3 — Draft + critical challenge** |

Ambiguous? Default to D2. Upgrade to D3 if during sub-phase 1 the atom's criticality becomes clearer.

### D1 — Draft review

**Turns:** 2–6. **Time:** 5–10 min.

**Flow:**
1. Agent loads context; leans on the nearest sibling or strongest existing pattern when possible
2. Agent drafts the complete spec inline
3. Anti-bloat and consistency probes run silently during drafting
4. Agent presents: *"Here's the draft. What's wrong or missing?"*
5. Human edits; agent iterates once
6. Propagate + handover

If input or output remains ambiguous after the first review, the agent opens a small number of targeted contract questions before finalizing. D1 should still feel like review, not interrogation.
Primitive-shape ambiguity counts as contract ambiguity. If a primitive field appears to carry structure, the agent must resolve that before exiting D1.

**Anti-bloat and consistency probes run during drafting** — any probe that would surface becomes a note or decision point in the draft:

```yaml
logic:
  - "WHEN input.id IS NULL THEN RETURN USR.VAL.004"
  # ^ consistency check: pol.usr.validate_all_ids applies WRITES_DB atoms;
  #   without this guard the atom would violate the policy.
```

### D2 — Draft + focused decisions (default)

**Turns:** 4–10. **Time:** 10–20 min.

**Flow:**
1. Agent loads context
2. Agent drafts the full spec block and likely verification from context
3. Agent presents the draft plus:
   - assumptions made
   - decision points
   - conflicts or missing facts
   - proposed L0 and module cascades
4. Human answers only the targeted questions where multiple valid choices exist
5. **Consistency probes fire** after the first draft and again only for sections materially changed by the review
6. Agent runs anti-bloat probes for every L0 entity still about to be created
7. Agent revises and presents the updated spec block
8. Human reviews the revised spec; iterates
9. Propagate + handover

**Contract review rule.** Input and output are drafted by default. The agent only opens explicit contract questions if the contract is not confidently inferable, if the choice affects downstream callers or types, or if the atom is carrying enough risk that contract precision matters.
**Primitive-shape rule.** Inline primitive fields across `input`, `output.success`, `props`, `local_state`, `input_distribution`, and `output_distribution` get a shape review before the draft is presented. If the field is parsed, split, pattern-matched, used as a discriminator, or consumed structurally by another atom, `shape` must be drafted or escalated as a mandatory decision point. "It's just a string" is not an acceptable final state for a structured wire format.

### D3 — Draft + critical challenge

**Turns:** 8–16. **Time:** 20–40 min.

Reserved for atoms where the stakes warrant extra scrutiny: money movement, security, module-defining business rules, data integrity, and probabilistic models.

The agent still drafts first. The difference is that review continues through structured challenge areas after the first draft:

| Challenge area | Focus |
|---|---|
| 1 | Business-critical correctness |
| 2 | Security / authorization |
| 3 | Data integrity / invariants |
| 4 | External failure handling |
| 5 | Caller / flow expectations |

Within each area, the agent asks only the unresolved decision points. Input and output contract questions still stay ambiguity-gated; they do not become a field-by-field interrogation unless the atom's risk genuinely demands it.
Structured primitive fields count as contract ambiguity here too. A D3 atom cannot exit review while a downstream-consumed primitive remains structurally unspecified.

---

## 4. L0 propagation — tiered policy

Different L0 entity types carry different stakes and get different write policies.

| Entity | Tier | Policy |
|---|---|---|
| New types | **Auto-write** | Agent writes to `L0_registry.yaml`, summarizes at end of session |
| New constants | **Auto-write with skepticism flag** | If value has a single consumer, agent flags: *"`<CONST>` is used only by `<atom>`. Promote to L0 constant, or leave as a local value?"* |
| New errors | **Confirm** | Agent asks before each write: *"Adding `<CODE>: <message>` under category `<cat>`. L1 default action for this category is `<action>`. Proceed?"* |
| New error categories | **Confirm + rationale** | Explicit confirmation; rationale recorded in L0 changelog |
| New side-effect markers | **Confirm + rationale** | Schema-level impact; same treatment |
| New external_schemas | **Reject** | Should have been declared in discover; agent redirects the human back to discover rather than allowing late addition |

### Why the tiers

- **Types** are low-stakes because they're scoped to the atoms that reference them. Forking a type is cheap; consolidation is a later-audit concern.
- **Constants** are moderate — they're project-wide, but adding one is reversible. The skepticism flag catches the common failure mode (promoting a local magic number to an L0 constant unnecessarily).
- **Errors** are higher-stakes because every error code participates in L1 `failure.defaults` policy — adding an error without confirmation silently extends what L1 must handle.
- **Error categories, side-effect markers** are schema-level — they change what validation rules mean across the whole project. Confirming ensures the human sees the impact.
- **External schemas** are discover-territory; allowing them at forge-atom would mean late-stage discovery of project dependencies the discover sub-phase should have caught.

---

## 5. Anti-bloat probes — reuse-before-create

Every time a new L0 entity is about to be written, the relevant reuse scan fires.

### Type reuse probe

Before writing a new type:

```bash
forge find <field_keywords_from_proposed_type> --kind type --spec-dir <dir>
```

Present matches advisorily:

> *"Before defining `<proposed_type>` with fields `<fields>`, I found existing types that may fit:*
> *- `<candidate_1>` — `<field summary>` — overlap: `<signal>`*
> *- `<candidate_2>` — ...*
> *Options: (a) reuse `<candidate_1>` as-is, (b) extend `<candidate_1>` with nullable additions, (c) new type — what distinguishes this from `<candidate_1>`?*
> *Which?"*

### Error reuse probe

Before writing a new error:

```bash
forge find <failure_keyword> --kind error --spec-dir <dir>
```

Scan prioritizes the same category first (e.g., for a proposed VAL error, show existing VAL errors before widening to other categories). Present matches:

> *"Before adding `<proposed_code>: <message>`, I found existing errors that may cover this case:*
> *- `<existing_code_1>` — `<message>` — same category*
> *Options: (a) reuse `<existing_code_1>`, (b) new code — what case does it cover that `<existing_code_1>` doesn't?*
> *Which?"*

### Constant skepticism probe

Before writing a new constant:

1. Scan the project for references to the proposed value via `forge find <value> --spec-dir <dir>` (or via `const.<NAME>` lookups in all atoms' logic).
2. If the value has only one atom-level consumer, flag:

> *"`<CONST_NAME>` appears to be used only in `<atom_id>`. Two readings:*
> *(a) Promote to L0 constant — it's project-wide policy (compliance threshold, protocol version, standard timeout)*
> *(b) Leave as a local value inside the atom's logic — it's an implementation detail, not policy*
> *Which?"*

All advisory. Human may override with no justification required. The probe just makes "is this really project-wide?" visible at creation time.

---

## 6. Consistency probes — cross-system contradiction checks

Seven check classes, fired at anchored moments. Each uses existing CLI primitives (`forge inspect`, `forge context`, `forge find`) — no new sensing infrastructure needed.

### Check classes

| # | Check | What it detects | How |
|---|---|---|---|
| 1 | **Policy** | Atom behavior violates a policy applied to its module | Iterate module's `policies`; evaluate each policy's `applies_when` against atom's side_effects / id / markers |
| 2 | **Sibling atom** | Another atom in same module makes overlapping guarantees that conflict | `forge inspect <mod>` → read sibling specs; compare invariants on shared types |
| 3 | **Called-atom contract** | Atom ignores `failure_modes` of a downstream atom it invokes | `forge inspect <called>` → cross-check declared failures against this atom's TRY/CATCH coverage |
| 4 | **L1 convention** | Atom contradicts project-wide defaults (auth posture, audit, idempotency) | Read L1; check atom's markers against `security.resource_authorization`, `audit.triggers`, `idempotency.key_source` |
| 5 | **Access-permission** | Atom references external/env/network not in module's whitelist | Parse atom's logic for `external.X.Y`, `env.Z`; check against module's `access_permissions` |
| 6 | **Type invariant** | Atom produces values that violate its output type's invariants | Read L0 type invariants for input/output types; cross-check against logic branches that produce output values |
| 7 | **Event contract** | Atom emits an event with payload shape diverging from consumer expectations | `forge find <event_name>` → find consumer atoms; compare emitted payload against consumers' declared payload types |

### Fire moments

**D1 (draft review):** All seven checks run silently *during* drafting. Any contradiction detected is surfaced as a note or decision point in the draft, so the human sees the reasoning while reviewing.

**D2 (draft + focused decisions):** Two anchored moments:
- **After the first draft, before human review.** Agent silently runs all seven checks against the drafted behavior. Any contradictions surface as option-sets before the review questions.
- **After the human's decisions, before the revised spec is presented.** A second sweep catches contradictions that only become visible once the draft has been updated.

**D3 (draft + critical challenge):** Relevant checks run after each challenge area. Security / authorization chiefly fires 1/4/5; data integrity chiefly fires 2/3/6; caller / flow expectations chiefly fire 3/7.

### Primitive shape review

This is not one of the seven contradiction probes. It is a required draft hygiene check run during sub-phase 1 before the review is shown to the human.

For each inline primitive field in:
- `input`
- `output.success`
- `props`
- `local_state`
- `input_distribution`
- `output_distribution`

ask:
1. Is the field opaque pass-through?
2. Is it parsed, split, pattern-matched, discriminated, or structurally inspected?
3. Do downstream atoms or event consumers depend on that structure?

Outcomes:
- If opaque: leave bare `type` and move on.
- If structured and already knowable: draft `shape`.
- If structured but ambiguous: raise a mandatory decision point.

Suggested prompt:

> *"`<field>` is currently a bare `<type>`. Do other atoms or branches depend on its internal structure? If yes, I need to capture that with `shape` before we finalize this atom."*

### Presentation template

When a contradiction surfaces, the agent uses this structure:

```
Flag: <named constraint> — <short description>

Context: <the specific conflict — what the human said vs. what the constraint requires>

Options to resolve:
(a) <option 1> — <implication>
(b) <option 2> — <implication>
(c) <option 3 — usually "the constraint is outdated, revise it"> — <implication>

Which fits?
```

Example:

> *"Flag: policy `pol.usr.require_email_verification` applies here (atom writes users table).*
> *Context: your case 1 says account is created and user can log in immediately. Policy requires `after_success: assert verification_email dispatched OR status=PENDING`.*
> *Options:*
> *(a) Atom sets status=PENDING on creation (verification satisfies policy later via separate atom)*
> *(b) Atom opts out of the policy with justification*
> *(c) Policy is outdated; revise it to allow immediate activation for trusted signup sources*
> *Which?"*

### Design principles

- **Targeted.** Agent names one constraint, presents options, moves on. Never dumps a list of "things to consider."
- **Named references.** Always cite the specific entity: `pol.X`, `atm.Y`, L1 section `security.resource_authorization`. Not "a rule somewhere."
- **Advisory.** Same as anti-bloat probes — surface the conflict, let the human resolve. Never block.
- **Contextual wording.** If the human said "cancel" in the case, the probe says "cancel" — not "this operation."
- **Quiet when clean.** If no contradictions surface, the probes are invisible. No narration for its own sake.

---

## 7. The four sub-phases

### Sub-phase 0 — Context load + review depth selection

**Actions:**
1. Run `forge context <atom_id>` to load stub + surrounding context (module, siblings, L0 so far, applied policies, L1 defaults, any L4 callers that already reference this atom).
2. Read `discovery-notes.md` for atom hints, persistence entity notes, open_questions.
3. If the stub's `spec` is partial from a prior session, enter confirm+resume mode: walk through each filled field, confirm or correct, then continue from the first unfilled field.
4. Confirm the stub description is still accurate; refine if vague.
5. Read the stub's declared side_effects (or infer from description if not yet declared) and **select the review depth** (D1 / D2 / D3). Announce.

**Exit condition:** review depth selected, human confirmed description, context loaded.

### Sub-phase 1 — Specification

Branches by review depth (§3). Produces the full `spec` block.

Required during this sub-phase: run the primitive shape review and resolve every structured primitive to either `shape` or an explicit opaque-token confirmation before the spec is considered complete.

**Exit condition:** `spec` block complete per kind. Verification items accumulated during the interview.

### Sub-phase 2 — Verification finalization

1. Check L1 floors: `min_property_assertions`, `min_edge_cases`, `min_example_cases`.
2. If any floor is unmet, probe for additional examples or edge paths until the floor is met.
3. For `kind: MODEL` atoms, add `bounds_verification` sub-section (explicitly enumerate how acceptable_bounds will be validated).

**Exit condition:** all L1 floors met; MODEL atoms have bounds_verification.

### Sub-phase 3 — Propagation + validation + handover

1. **Write L0 entries** per the tiered policy (§4).
2. **Complete module cascades:**
   - `persistence_schema.datastores`: if atom has `WRITES_DB`, add the relevant datastore entry with `form`
   - `access_permissions`: extend `env_vars`, `secrets`, `network`, `external_schemas` for anything the atom references
   - `interface.entry_points`: if this atom is externally-triggered, complete the stub entry point (endpoint, method, event, request_type, response_type, security)
3. **Run `forge context <atom_id>`** — exit code must be 0. Any unresolved references mean the elicitation isn't complete; resolve before handover.
4. **Dual-path handover:**

   **Case A — more atoms in this module unfilled:**
   > *"Next atom in `<MOD>`: `<next_id>` (most downstream callers / hardest-to-get-right). Continue in this session — context stays warm — or `/clear` between atoms if preferred."*

   **Case B — module fully elicited:**
   > *"`<MOD>` complete. To continue with next module: `/clear`, then `/forge-atom` auto-picks. Or `/forge-audit <MOD>` to challenge the module's completed specs."*

**Exit condition:** `forge context` returns 0; handover presented.

---

## 8. Kind-specific spec shape notes

The review depth (D1/D2/D3) governs the *review structure*; the atom's `kind` governs the *spec block fields* that must be populated at the end.

### PROCEDURAL

```yaml
spec:
  input: <type_id | inline_fields>
  output:
    success: <type_id | inline_fields>
    errors: [<error_code>, ...]
  side_effects: [<marker>, ...]
  invariants:
    pre: [<expression>, ...]
    post: [<expression>, ...]
  logic: [<guarded_step>, ...]
  failure_modes:
    - trigger: <string>
      error: <error_code>
```

Default for handlers, functions, pipeline stages, event processors, CLI commands.

### DECLARATIVE

```yaml
spec:
  target: <string>                    # database_schema, infrastructure, style, config
  desired_state: <structure>
  reconciliation:
    strategy: migration | replace | merge
    on_conflict: fail_and_report | overwrite | manual
  failure_modes:
    - trigger: <string>
      error: <error_code>
```

Target + desired_state + reconciliation. In D2, review usually focuses on whether the drafted desired state and reconciliation strategy are accurate, with a grounding example only if the draft is too thin.

### COMPONENT

```yaml
spec:
  props: <inline_fields>
  local_state: <inline_fields | null>
  composes: [<atom_id>, ...]
  events_emitted:
    - name: <string>
      payload_type: <type_id | null>
  render_contract: [<render_rule>, ...]
  invariants: [<expression>, ...]
```

UI atoms. Render contract uses `ALWAYS RENDER / WHEN ... THEN RENDER / ON event DO action`. In D2, review usually checks the drafted states and emitted events first, then asks targeted questions like "what's missing in the loading or error state?" only if the contract is still unclear.

### MODEL

```yaml
spec:
  input_distribution: <inline_fields>
  output_distribution: <inline_fields>
  acceptable_bounds:
    <metric_name>: <threshold_expression>
  training_contract:
    data_source: <artifact_id>
    min_samples: <integer>
    drift_check_frequency: <string>
    retrain_trigger: <expression>
  fallback:
    when: <condition>
    invoke: <atom_id>   # must resolve to a PROCEDURAL atom
```

Always D3 — probabilistic contracts need bounds discipline. The review surfaces acceptable_bounds (false-positive rate, recall, calibration metrics), training contract (data source as an L3 artifact), and the deterministic fallback atom.

---

## 9. What `forge-atom` does NOT produce

Elicit-atom is the *end* of the spec pipeline for a single atom. It writes nearly everything. The only things it deliberately doesn't touch:

| Not produced | Reason |
|---|---|
| New modules | That's discover's job; adding modules mid-elicitation would be a scope break |
| New external_schemas | Discover should have declared them; late addition is a signal to go back to discover |
| New policies | Policies are cross-cutting; creating one mid-elicitation (for one atom) indicates the atom is in the wrong module or a policy was missed in discover |
| L4 flows / journeys | Composition-level concern; forge-atom produces the atoms that `forge-compose` turns into flows/journeys |
| Other atoms' spec blocks | One atom per forge-atom invocation. Cross-atom pressure goes into `open_questions`, resolved in subsequent elicitations |

---

## 10. Artifact schemas

### Complete atom spec (after forge-atom exit)

See the L3 schema template at `src/templates/L3/L3_behavior.schema.md`. Every stub field now populated per the atom's kind. Verification meets L1 floors. Changelog entry appended for the elicitation.

### L0 additions (per session)

Each session may add entries under any of:
- `L0_registry.yaml#types` — auto-written
- `L0_registry.yaml#errors` — confirmed
- `L0_registry.yaml#constants` — auto-written with skepticism flag for single-consumer values

Each addition carries a changelog entry with date, version, and description ("Added by forge-atom during `<atom_id>` elicitation").

### Module updates

`L2_modules/<MOD>.yaml` fields that forge-atom may mutate:

- `persistence_schema.datastores` — new entry if atom writes state
- `access_permissions.env_vars / secrets / network / external_schemas` — extended for atom's references
- `interface.entry_points` — stub completion (paths, methods, types, security)
- `changelog` — append entry for the elicitation

### Discovery notes updates

`discovery-notes.md` atom entry status: `stubbed` → `elicited`. Any consistency probes that surfaced unresolved tensions (e.g., a policy that needs revision) get added to `open_questions`.

---

## 11. Compatibility

Format-agnostic. The skill artifact at `.agents/skills/forge-atom/SKILL.md` references this framework under `references/framework.md` for progressive disclosure — load on demand for depth on review depth selection, consistency probe details, or artifact schemas.

---

## 12. Open design questions (for future iteration)

- **When should forge-atom re-enter after audit?** Audit may reveal an atom needs spec revision. Should that invoke forge-atom's partial-spec resume, or a dedicated revision mode?
- **How should cross-module impact propagation work?** If forge-atom modifies an L0 type used by other atoms, those atoms' verification may no longer be accurate. Current design flags in `open_questions`; a future version could automatically re-run verification checks on affected atoms.
- **D1 auto-drafting quality.** D1 depends on the agent producing a good first draft. What's the fallback if the draft is consistently wrong? Current design assumes escalation to D2 after a weak first review; a future version could formalize that threshold.
- **Kind hybrids.** The framework insists one kind per atom. In practice, some atoms blur boundaries (a PROCEDURAL atom that partly manages COMPONENT state). Current design decomposes; future could allow explicit "primary kind" with documented hybrid behavior.
