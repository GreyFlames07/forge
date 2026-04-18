# forge-atom — Framework

This document describes the **mental model** for `forge-atom`: the stages, the three interview shapes, the consistency probes, the anti-bloat protocol, and the artifact cascades produced. It is **not** the SKILL.md; it is the source of truth from which any skill artifact is authored.

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
| Interview feel | Workshop | Depth interrogation | **Contract specification** |
| Duration | 1–2 hours total | ~10–15 min / module | **~10–60 min / atom (shape-dependent)** |
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

1. **Shape matches complexity, not atom count.** Simple atoms get Shape A (draft-then-review). Standard atoms get Shape B (example-driven extraction). High-stakes atoms get Shape C (structured deep-dive). The shape is announced explicitly at sub-phase 0 exit: *"Side effects suggest Shape B — example-driven extraction."*
2. **Logic is prose-first.** Human describes steps in natural language; agent normalizes to `WHEN / LET / CALL / RETURN / EMIT / SET / TRY` DSL for review. The human never has to produce DSL directly.
3. **Verification is implicit.** Example cases walked through ARE example_cases. Edge paths probed ARE edge_cases. Invariants true across all cases ARE property_assertions. L1 floors met by construction, not by a separate "now let's write tests" phase.
4. **Consistency probes are targeted, not exhaustive.** When a contradiction surfaces, the agent names it specifically (policy / sibling / called-atom / etc.) and presents options. When nothing surfaces, the probes are invisible — no narration.
5. **Anti-bloat probes fire at every L0 create.** Before writing a new type / error / constant, run the relevant reuse scan via `forge find`. Present matches advisorily.
6. **Within-module chain mode.** Context stays warm across atoms in the same module — sibling patterns, shared types, the just-elicited siblings inform subsequent atoms. `/clear` happens between modules, not between atoms (unless human opts in).
7. **Stubs get filled; never recreated.** Partial spec handling is confirm+resume: show existing fields, allow corrections, then continue from the first unfilled field. Never wipe and restart unless the human explicitly asks.

---

## 3. Shape selection

The agent selects the interview shape from the stub's surfaced complexity at sub-phase 0 exit. **Selection is deterministic, not adaptive-mid-flow.** The agent announces the pick so the human knows what to expect.

### Selection rules

| Condition | Shape |
|---|---|
| `side_effects` is `[PURE]` OR only `READS_*` markers, AND a sibling atom with a similar pattern already exists in the module | **Shape A** |
| Any `WRITES_*`, `EMITS_EVENT`, or `CALLS_EXTERNAL` marker present | **Shape B** (default) |
| All three of `WRITES_DB + CALLS_EXTERNAL + EMITS_EVENT`, OR module flagged "hardest to get right" in discover, OR `kind: MODEL` | **Shape C** |

Ambiguous? Default to Shape B. Upgrade to Shape C if during sub-phase 1 the atom's complexity becomes clearer.

### Shape A — Draft-then-review

**Turns:** 5–10. **Time:** 10–20 min.

**Flow:**
1. Agent loads context; reads the nearest-sibling specced atom as a pattern source
2. Agent drafts the complete spec inline
3. Agent presents: *"Here's the draft. What's wrong?"*
4. Human edits; agent iterates
5. Propagate + handover

**Anti-bloat and consistency probes run during drafting** — any probe that would surface is inlined as a comment in the draft:

```yaml
logic:
  - "WHEN input.id IS NULL THEN RETURN USR.VAL.004"
  # ^ consistency check: pol.usr.validate_all_ids applies WRITES_DB atoms;
  #   without this guard the atom would violate the policy.
```

### Shape B — Example-driven extraction (default)

**Turns:** 12–20. **Time:** 30–45 min.

**Flow:**
1. Agent loads context
2. Agent asks for one concrete example case: input → steps → output
3. Human walks the happy path
4. Agent asks for 2–3 more cases (alternate inputs, failure paths)
5. **Consistency probes fire** between case walk-throughs and extraction
6. Agent runs anti-bloat probes for every L0 entity about to be created
7. Agent extracts and presents the full spec block (input type, output type, side_effects, logic DSL, failure_modes, invariants, verification)
8. Human reviews the extracted spec; iterates
9. Propagate + handover

**Extraction pattern.** The agent produces the spec FROM the case walk-throughs, not ALONGSIDE them. The walk-throughs are the elicitation medium; the spec block is the artifact.

- **Input shape** — field names + types referenced in the first steps of each case
- **Output shape** — what each case returns
- **Side effects** — verbs used across cases map to L0 markers (WRITES_DB from "insert," EMITS_EVENT from "publish," CALLS_EXTERNAL from "POST to Stripe," etc.)
- **Logic DSL** — normalized steps from the walkthrough, covering the branches surfaced by alternate cases
- **Failure modes** — failure-path cases give trigger → error_code pairs
- **Invariants (pre)** — what was true on entry in every case
- **Invariants (post)** — what was true on successful exit in every case
- **Verification** — the 2–3 example cases become `example_cases`; edge paths probed during cases become `edge_cases`; what held across all cases becomes `property_assertions`

### Shape C — Structured deep-dive

**Turns:** 25–35. **Time:** 45–60 min.

**Six sequential passes**, each with consistency probes firing after the pass completes:

| Pass | Focus |
|---|---|
| 1 | Input contract |
| 2 | Output contract (success shape + error set) |
| 3 | Side effects (which L0 markers apply; what L1 conventions activate) |
| 4 | Invariants (pre + post) |
| 5 | Logic (prose-first, DSL-normalized) |
| 6 | Failure modes (trigger → error_code mapping) |

Reserved for atoms where the stakes warrant the extra ceremony: money movement, security, data integrity, probabilistic models.

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

**Shape A (draft-then-review):** All seven checks run silently *during* drafting. Any contradiction detected is inlined as a comment in the draft, so the human sees the reasoning while reviewing.

**Shape B (example-driven):** Two anchored moments:
- **After case walk-throughs, before extraction.** Agent silently runs all seven checks against the described behavior. Any contradictions surface as option-sets before the extracted spec is presented.
- **After extraction, before the spec review.** A second sweep catches contradictions that only become visible once the logic DSL is normalized.

**Shape C (structured deep-dive):** Relevant checks run after each of the six passes. After pass 3 (side effects), checks 1/4/5 fire. After pass 5 (logic), checks 2/3/6 fire. After pass 6 (failure modes), check 7 fires.

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

### Sub-phase 0 — Context load + shape selection

**Actions:**
1. Run `forge context <atom_id>` to load stub + surrounding context (module, siblings, L0 so far, applied policies, L1 defaults, any L4 callers that already reference this atom).
2. Read `discovery-notes.md` for atom hints, persistence entity notes, open_questions.
3. If the stub's `spec` is partial from a prior session, enter confirm+resume mode: walk through each filled field, confirm or correct, then continue from the first unfilled field.
4. Confirm the stub description is still accurate; refine if vague.
5. Read the stub's declared side_effects (or infer from description if not yet declared) and **select the shape** (A / B / C). Announce.

**Exit condition:** shape selected, human confirmed description, context loaded.

### Sub-phase 1 — Specification

Branches by shape (§3). Produces the full `spec` block.

**Exit condition:** `spec` block complete per kind. Verification items accumulated during the interview.

### Sub-phase 2 — Verification finalization

1. Check L1 floors: `min_property_assertions`, `min_edge_cases`, `min_example_cases`.
2. If any floor is unmet (usually only in Shape A), probe for additional cases until the floor is met.
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

The interview shape (A/B/C) governs the *interview structure*; the atom's `kind` governs the *spec block fields* that must be populated at the end.

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

Target + desired_state + reconciliation. Interview compresses in Shape B — one case walk-through of "the desired end state looks like X" plus the reconciliation strategy.

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

UI atoms. Render contract uses `ALWAYS RENDER / WHEN ... THEN RENDER / ON event DO action`. Interview in Shape B walks through "what does the screen look like in state X?" for 2–3 states.

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

Always Shape C — probabilistic contracts need bounds discipline. The interview surfaces acceptable_bounds (false-positive rate, recall, calibration metrics), training contract (data source as an L3 artifact), and the deterministic fallback atom.

---

## 9. What `forge-atom` does NOT produce

Elicit-atom is the *end* of the spec pipeline for a single atom. It writes nearly everything. The only things it deliberately doesn't touch:

| Not produced | Reason |
|---|---|
| New modules | That's discover's job; adding modules mid-elicitation would be a scope break |
| New external_schemas | Discover should have declared them; late addition is a signal to go back to discover |
| New policies | Policies are cross-cutting; creating one mid-elicitation (for one atom) indicates the atom is in the wrong module or a policy was missed in discover |
| L4 flows / journeys | Composition-level concern; forge-atom produces the atoms that flows compose |
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

Format-agnostic. The skill artifact at `.agents/skills/forge-atom/SKILL.md` references this framework under `references/framework.md` for progressive disclosure — load on demand for depth on shape selection, consistency probe details, or artifact schemas.

---

## 12. Open design questions (for future iteration)

- **When should forge-atom re-enter after audit?** Audit may reveal an atom needs spec revision. Should that invoke forge-atom's partial-spec resume, or a dedicated revision mode?
- **How should cross-module impact propagation work?** If forge-atom modifies an L0 type used by other atoms, those atoms' verification may no longer be accurate. Current design flags in `open_questions`; a future version could automatically re-run verification checks on affected atoms.
- **Shape A auto-drafting quality.** Shape A depends on the agent producing a good first draft. What's the fallback if the draft is consistently wrong? Current design assumes iteration; a future version could escalate to Shape B after N failed iterations.
- **Kind hybrids.** The framework insists one kind per atom. In practice, some atoms blur boundaries (a PROCEDURAL atom that partly manages COMPONENT state). Current design decomposes; future could allow explicit "primary kind" with documented hybrid behavior.
