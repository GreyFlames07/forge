---
name: forge-atom
description: >
  Use this skill when the user needs to elicit the complete L3 spec for a
  single atom stub that forge-decompose created — i.e., an atom exists in
  L3_atoms/ with id, kind, owner_module, description set, but its spec
  block is empty or partial. Activates on phrases like "elicit atom X",
  "fill in the spec for atom X", "spec out atom X", "complete the atom",
  or when forge context <atom_id> shows the spec block as empty. Drives
  one of three interview shapes selected by complexity (A: draft-then-
  review for simple atoms; B: example-driven extraction by default; C:
  structured 6-pass deep-dive for high-stakes atoms). Produces the full
  spec block, verification meeting L1 floors, new L0 entries (types,
  errors, constants) the atom forces, and module-level cascades
  (persistence_schema datastores, access_permissions, filled entry
  points). Runs anti-bloat probes (reuse-before-create) and consistency
  probes (7 cross-system contradiction checks) throughout.
---

# forge-atom

Take one atom stub and produce a complete, implementation-ready L3 spec plus every cascade the atom forces. You pick one of three interview shapes based on atom complexity, extract the spec from examples (for most atoms), run anti-bloat and consistency probes at every create/decide moment, and finalize with L0 writes + module updates + validation.

Full mental model, shape selection logic, consistency probe details, and artifact schemas in `references/framework.md` (~650 lines). Load on demand:
- `§3` for shape selection rules and the three interview flows
- `§4` for L0 propagation tier policy
- `§5` for anti-bloat probe templates
- `§6` for consistency probe check classes and fire moments
- `§8` for kind-specific spec block requirements
- `§10` for artifact schemas

Otherwise this file is self-sufficient for routine operation.

## Non-negotiables

1. **One concept per turn.** Ask one thing, wait, move on.
2. **Shape matches complexity.** Simple atoms → Shape A. Standard → Shape B. High-stakes → Shape C. Announce the shape at sub-phase 0 exit.
3. **Logic is prose-first.** Human describes steps in natural language; you draft the DSL; human reviews. Never force the human to produce DSL syntax.
4. **Verification emerges implicitly.** Example cases walked through BECOME `example_cases`. Edge paths BECOME `edge_cases`. Invariants held across all cases BECOME `property_assertions`. L1 floors met by construction, not a separate phase.
5. **Anti-bloat probes fire before every L0 create.** Run `forge find` for types, errors, constants. Present matches advisorily. Never silently create.
6. **Consistency probes are targeted, named, quiet when clean.** When a contradiction surfaces, cite the specific entity (`pol.X`, `atm.Y`, L1 section) and present options. Never narrate "I checked X, Y, Z" when no conflict exists.
7. **Partial spec: confirm+resume.** If fields exist from a prior session, acknowledge each, let the human correct, then continue from the first unfilled field. Never wipe and restart unless explicitly asked.
8. **Within-module chain mode.** Stay in one session across atoms in the same module. `/clear` between modules, not between atoms.
9. **Stubs get filled, never recreated.** If an atom file already exists as a stub, you are completing it. You never write a new stub.

Full rationale: `references/framework.md §2`.

## Workflow

### Step 1 — Load context + select shape

Run:
```bash
forge context <atom_id> --spec-dir <spec-dir>
```

Read what comes back:
- The stub (id, kind, owner_module, description, current spec state)
- Owning module (tech_stack, policies applied, access_permissions, dependency_whitelist)
- Sibling atoms (already-elicited atoms in the same module — their patterns inform this one)
- L0 so far (existing types, errors, constants — what can be reused)
- L1 conventions (defaults that activate once side_effects are declared)
- Any L4 callers (flows, journeys) and their declared `on_error` expectations

Also read `discovery-notes.md` for the atom's entity hints and any `open_questions` that reference it.

**If the stub's spec is partial from a prior session:**
1. List each filled field.
2. Walk through each: *"I see `<field>` is set to `<value>` — still accurate, or revise?"*
3. After all existing fields confirmed (or corrected), continue from the first unfilled field.

**If the stub description is vague:**
Refine it in one turn before proceeding: *"The description reads `<current>`. In one sentence: what does this atom actually do? (Describe purpose, not implementation.)"*

**Shape selection.** Read the stub's declared `side_effects`, or infer from the description:

| Condition | Shape |
|---|---|
| `side_effects` = `[PURE]` OR only `READS_*`, AND a sibling with similar pattern exists | **A** (draft-then-review) |
| Any `WRITES_*`, `EMITS_EVENT`, or `CALLS_EXTERNAL` marker | **B** (example-driven — default) |
| All of `WRITES_DB + CALLS_EXTERNAL + EMITS_EVENT` combined, OR module tagged hardest-to-get-right, OR `kind: MODEL` | **C** (structured deep-dive) |

Ambiguous? Default to Shape B. You can upgrade to Shape C mid-flow if complexity warrants.

**Announce the shape:**
> *"Side effects suggest Shape B — example-driven extraction. I'll ask for 2–3 example cases and extract the spec from them."*

### Step 2 — Run the chosen shape (sub-phase 1)

---

#### Shape A — Draft-then-review

1. **Load sibling patterns.** Identify the most similar already-elicited atom in the module; use its spec as the drafting pattern.
2. **Draft the complete spec inline.** Fill in input, output, side_effects, invariants, logic, failure_modes. Match the sibling's style for consistency.
3. **Run anti-bloat and consistency probes silently during drafting.** Any contradictions or reuse opportunities surface as inline comments in the draft:
   ```yaml
   logic:
     - "WHEN input.user_role != 'admin' THEN RETURN SEC.SEC.001"
     # ^ policy pol.<name> applies here (WRITES_DB on <table>); line added to satisfy it.
   ```
4. **Present the draft:** *"Here's the draft. What's wrong?"*
5. **Iterate based on the human's corrections.**
6. Skip to **Step 3 — Verification finalization**.

Shape A exits when the human confirms "looks good" to the draft after any edits.

---

#### Shape B — Example-driven extraction (default)

1. **Ask for case 1 (happy path):**
   > *"Give me one concrete case. What input goes in, what steps does the atom take, what comes out?"*
   
   Let the human walk it step by step in their own words. Don't interrupt for structure — capture the narrative.

2. **Ask for case 2 (alternate path or failure):**
   > *"Second case — what happens when `<specific_edge>` happens?"*
   
   Example `<specific_edge>`: duplicate input, missing required field, downstream failure, concurrent call.

3. **Ask for case 3 (another alternate or failure path):**
   Similar.

4. **Fire consistency probes** (between case 3 and extraction):
   Silently run the 7 check classes against what's been described. If any surface, pause extraction and present each as a targeted option-set. See `## Consistency probes` below.

5. **Fire anti-bloat probes** for every L0 entity about to be created:
   - Each new type → run `forge find <keywords> --kind type`
   - Each new error → run `forge find <keyword> --kind error`
   - Each new constant → scan for single-consumer status
   Present matches advisorily. See `## Anti-bloat probes` below.

6. **Extract and present the full spec block.** The spec is derived from the case walkthroughs, not asked-for as separate fields:
   - Input shape ← fields referenced in case openings
   - Output shape ← what each case returns
   - Side effects ← verbs used across cases (insert → WRITES_DB, publish → EMITS_EVENT, etc.)
   - Logic DSL ← normalized steps from the walkthroughs covering all branches
   - Failure modes ← failure-path cases give trigger → error_code pairs
   - Invariants pre ← what was true on entry across all cases
   - Invariants post ← what was true on successful exit across all cases
   - Verification (see Step 3) ← the 2–3 cases populate `example_cases`; edge paths populate `edge_cases`; cross-case constants populate `property_assertions`

   Present the full block: *"Here's the extracted spec. Review — what's wrong?"*

7. **Iterate based on human corrections.** When the human revises a field, check if the revision affects other fields (e.g., changing output shape may affect logic's RETURN statements). Propagate consistently.

8. Proceed to **Step 3 — Verification finalization**.

---

#### Shape C — Structured deep-dive

Six sequential passes. Consistency probes fire after relevant passes.

**Pass 1 — Input.** *"What fields does the atom accept? Required vs optional. Types."* Run type reuse probe if creating a new type.

**Pass 2 — Output.** *"Success shape. Error codes that can be returned."* Run type reuse for success shape; error reuse probe per error code.

**Pass 3 — Side effects.** *"Which L0 markers apply? WRITES_DB? EMITS_EVENT? CALLS_EXTERNAL? READS_ARTIFACT?"* Fire consistency probes 1 (policy), 4 (L1 convention), 5 (access-permission).

**Pass 4 — Invariants.** *"Preconditions that must hold on entry. Postconditions that must hold on successful exit."*

**Pass 5 — Logic.** Prose-first; agent normalizes to DSL. Fire consistency probes 2 (sibling atom), 3 (called-atom contract), 6 (type invariant).

**Pass 6 — Failure modes.** *"Map each trigger to an error code. Every error in output.errors must have a trigger. Every failure_mode must have an error in output.errors."* Fire consistency probe 7 (event contract).

Proceed to **Step 3 — Verification finalization**.

---

### Step 3 — Verification finalization (sub-phase 2)

Check L1 verification floors: `min_property_assertions`, `min_edge_cases`, `min_example_cases`. These typically come from L1 `verification.floors`.

For Shape B, verification is usually satisfied by construction (cases = example_cases, edge paths = edge_cases). For Shape A, you may need to probe for additional cases to meet the floor.

**If a floor is unmet:**
> *"L1 requires at least <N> <kind>. We have <M>. Give me one more — specifically, what about <suggested_edge_case_based_on_atom_surface>?"*

**For MODEL atoms:** add the required `bounds_verification` sub-section. Probe for how each `acceptable_bounds` metric will be measured in production.

**Exit condition:** all L1 floors met; MODEL atoms have `bounds_verification`.

### Step 4 — Propagation + validation + handover (sub-phase 3)

**1. Write L0 entries per tier** (see `## L0 propagation` below):
- Types: auto-write, summarize at end
- Errors: confirm each before writing
- Constants: auto-write with skepticism flag if single-consumer
- New categories or markers: confirm + rationale

**2. Complete module cascades** in `L2_modules/<owner>.yaml`:
- If atom has `WRITES_DB`: add datastore entry to `persistence_schema.datastores` with `form` (relational / document / key_value / etc. — consult module's `tech_stack.managed_services` for hints)
- Extend `access_permissions.env_vars / secrets / network / external_schemas` for anything the atom references
- If atom is externally-triggered (there's a stub entry point in `interface.entry_points` pointing at this atom), complete it: `endpoint`, `method`, `event`, `request_type`, `response_type`, `security`

**3. Append changelog entries** to the atom file and any files touched.

**4. Validate:**
```bash
forge context <atom_id> --spec-dir <spec-dir>
```

Exit code 0 → zero unresolved refs → elicitation complete.
Exit code 2 → unresolved refs → investigate before handing over. Common cause: a called atom doesn't exist yet; add to `open_questions` if intentional (next forge-atom session catches it).

**5. Mark the atom `elicited`** in `discovery-notes.md`'s candidate list.

**6. Handover — dual path:**

**Case A — more atoms in this module unfilled:**
> *"`<atom>` elicited — <breakdown summary>.*
> *`<K>` atoms remain in `<MOD>`: `<list>`.*
> *Next recommendation: `<next_id>` (most downstream callers / hardest-to-get-right).*
> *Continue in this session — context stays warm — or `/clear` between atoms if preferred.*
> *Run: `/forge-atom <next_id>`"*

**Case B — module fully elicited:**
> *"`<atom>` elicited — `<MOD>` is now fully specced. All `<N>` atoms complete.*
> *To continue:*
> *- `/clear` then `/forge-atom` — auto-picks first unfilled atom in next module*
> *- `/forge-audit <MOD>` — challenge the module's completed specs before implementation"*

## Shape selection detail

Shape selection is **deterministic**, not adaptive-mid-flow. Pick at sub-phase 0 exit; announce; stick with it.

**Upgrade rule:** if mid-Shape-B you discover the atom is genuinely more complex than you thought (e.g., walkthrough reveals a fourth marker you missed, or human can't articulate bounds), you may upgrade to Shape C. Announce the upgrade: *"This is more complex than I initially gauged — switching to Shape C for the remaining passes."* Do NOT downgrade once started.

## L0 propagation

| Entity | Tier | Action |
|---|---|---|
| Types | Auto | Write to `L0_registry.yaml`, record in session summary |
| Constants | Auto + flag | Write; flag single-consumer constants: *"`<CONST>` appears only in `<atom>`. Keep as L0 constant, or demote to local value?"* |
| Errors | Confirm | *"Adding `<CODE>: <message>` under category `<cat>`. L1 default action: `<action>`. Proceed?"* |
| Error categories | Confirm + rationale | Changelog entry records the reason |
| Side-effect markers | Confirm + rationale | Same — schema-level impact |
| External schemas | Reject | *"External schemas are declared in forge-discover. If you genuinely need a new one, return to discover. Otherwise, reuse an existing schema."* |

## Anti-bloat probes

**Type reuse** — before writing any new `L0.types` entry:
```bash
forge find <field_keywords> --kind type --spec-dir <dir>
```

Present candidates:
> *"Before defining `<proposed_type>` with fields `<fields>`, I found:*
> *- `<candidate>` — `<field_summary>` — overlap: `<signal>`*
> *Options: (a) reuse, (b) extend with nullable additions, (c) new type — what distinguishes it?*
> *Which?"*

**Error reuse** — before writing any new `L0.errors` entry:
```bash
forge find <failure_keyword> --kind error --spec-dir <dir>
```

Scan the same category first. Present candidates:
> *"Before adding `<proposed_code>: <message>`, I found:*
> *- `<existing>` — `<message>` — same category*
> *Options: (a) reuse, (b) new — what case doesn't `<existing>` cover?*
> *Which?"*

**Constant skepticism** — before writing any new `L0.constants` entry:
If the proposed value appears in only one atom's logic, flag:
> *"`<CONST>` is used only in `<atom>`. Two readings:*
> *(a) Promote — it's project-wide policy (compliance, protocol version, standard timeout)*
> *(b) Keep local — implementation detail, not policy*
> *Which?"*

All advisory. Human may override without justification.

## Consistency probes

Seven check classes. Run silently; surface only when a contradiction is found. Always name the constraint explicitly.

| # | Check | What you compare |
|---|---|---|
| 1 | Policy | Module's `policies` → each policy's `applies_when` vs atom's side_effects / id pattern / markers |
| 2 | Sibling atom | `forge inspect <mod>` → sibling specs' invariants on shared types |
| 3 | Called-atom contract | `forge inspect <called>` → declared `failure_modes` vs this atom's TRY/CATCH coverage |
| 4 | L1 convention | L1 `security.resource_authorization`, `audit.triggers`, `idempotency.key_source` vs atom's markers |
| 5 | Access-permission | Atom logic references to `external.X.Y`, `env.Z`, network calls vs module's `access_permissions` whitelist |
| 6 | Type invariant | Input/output L0 type invariants vs logic branches that produce output values |
| 7 | Event contract | `forge find <event_name>` → consumer atoms' expected payload types vs emitted payload shape |

**Fire moments:**

- Shape A: all 7 checks silent during drafting; contradictions surface as inline comments in the draft
- Shape B: twice — after case walkthroughs (before extraction), and after extraction (before human review)
- Shape C: relevant checks after each pass (pass 3 fires 1/4/5; pass 5 fires 2/3/6; pass 6 fires 7)

**Presentation template:**

```
Flag: <named constraint> — <short description>

Context: <the specific conflict — what the human said vs what the constraint requires>

Options:
(a) <option 1> — <implication>
(b) <option 2> — <implication>
(c) <option 3 — usually "the constraint is outdated"> — <implication>

Which fits?
```

## Gotchas

- **The agent never produces DSL; it produces the spec block with DSL embedded.** Humans speak prose; you translate. Don't ask "what's the DSL for this?" — ask "what happens next?"
- **Do not write the `spec` block field-by-field in Shape B.** The whole point of extraction is the spec emerges from the cases. If you find yourself asking "what's the invariant?" separately from the case walkthroughs, you've drifted — back to asking for cases.
- **Consistency probes are silent when clean.** Do not announce "I ran 7 consistency checks — all clear." That's narration for its own sake. Only speak up when a probe actually surfaces a conflict.
- **Never skip anti-bloat probes.** Even for obviously-novel types. The scan is cheap; the human sees it's genuinely novel and confirms quickly; that's the point.
- **Partial specs are the default, not an edge case.** Most elicitations hit sessions with some fields filled (the description was sharpened in sub-phase 0; decompose populated side_effects hints). Confirm+resume is the main path, not an exception.
- **If `forge context <atom>` returns exit 2 with unresolved refs**, the elicitation is not done. Either the refs are typos (fix them) or they point at atoms not yet elicited (add to `open_questions` and still commit — future elicitation sessions will catch them).
- **Shape A requires a specced sibling as a pattern source.** If no sibling in the module has been elicited yet, downgrade to Shape B — you have no pattern to draft from.
- **External schemas at forge-atom are a signal, not a problem.** If the human says "we also call Twilio" and Twilio isn't in `L0.external_schemas`, don't add it — redirect: *"Twilio isn't declared in discover's L0 external_schemas. That's discover territory. To add it: `/forge-discover` to return to sub-phase 3."*

## forge CLI commands used

| Command | Used for |
|---|---|
| `forge context <atom_id>` | Sub-phase 0 context load (stub, module, siblings, L0, L1, callers) |
| `forge inspect <id>` | Check a specific called-atom's contract (consistency probe 3) |
| `forge find <q> --kind type` | Type reuse probe before any L0.types write |
| `forge find <q> --kind error` | Error reuse probe before any L0.errors write |
| `forge find <q>` (no kind) | Event contract probe (consistency check 7) — find atoms consuming a given event |
| `forge context <atom_id>` (end of sub-phase 3) | Final validation — exit 0 means elicitation complete |

## References

- `references/framework.md` — full mental model. Sections:
  - §2 operating principles rationale
  - §3 shape selection + flows
  - §4 L0 propagation tier policy
  - §5 anti-bloat probe templates
  - §6 consistency probe check classes
  - §7 sub-phase structure
  - §8 kind-specific spec shapes
  - §9 what forge-atom does NOT produce
  - §10 artifact schemas
- `assets/spec-review.template.md` — recommended structure for presenting extracted specs in Shape B
