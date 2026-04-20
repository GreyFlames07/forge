---
name: forge-atom
description: >
  Use this skill when the user needs to elicit the complete L3 spec for a
  single atom stub that forge-decompose created — i.e., an atom exists in
  L3_atoms/ with id, kind, owner_module, description set, but its spec
  block is empty or partial. Activates on phrases like "elicit atom X",
  "fill in the spec for atom X", "spec out atom X", "complete the atom",
  or when forge context <atom_id> shows the spec block as empty. Starts
  with a draft built from context, then runs one of three review depths
  selected by criticality (D1: draft review, D2: draft plus focused
  decisions, D3: draft plus critical challenge). Produces the full spec
  block, verification meeting L1 floors, new L0 entries (types, errors,
  constants) the atom forces, and module-level cascades
  (persistence_schema datastores, access_permissions, filled entry
  points). Runs anti-bloat probes (reuse-before-create) and consistency
  probes (7 cross-system contradiction checks) throughout.
---

# forge-atom

Take one atom stub and produce a complete, implementation-ready L3 spec plus every cascade the atom forces. Start by drafting the atom from the available context. Then ask only the decision questions the draft cannot settle, opening deeper challenge only when the atom is critical to the module's purpose or carries business, security, data, or MODEL risk. Routine atoms should usually resolve in one or two review passes.

Full mental model, review depth logic, consistency probe details, and artifact schemas in `references/framework.md` (~650 lines). Load on demand:
- `§3` for review depth rules and the three review flows
- `§4` for L0 propagation tier policy
- `§5` for anti-bloat probe templates
- `§6` for consistency probe check classes and fire moments
- `§8` for kind-specific spec block requirements
- `§10` for artifact schemas

Otherwise this file is self-sufficient for routine operation.

## Non-negotiables

1. **Draft first; question second.** If a plausible spec can be inferred from context, write the draft before asking broad elicitation questions.
2. **Review depth matches criticality.** Routine atoms get light review. Critical atoms get deeper decision points and challenge passes. Side effects inform the depth, but they do not automatically force the deepest flow.
3. **Ask only decision questions.** Do not ask the human to build the atom from scratch when the draft is already plausible. Open input or output contract questions only when ambiguity or risk remains.
4. **Logic is prose-first.** Human describes corrections in natural language; you draft or revise the DSL; the human reviews. Never force the human to produce DSL syntax.
5. **Verification emerges from draft + review.** Example cases, edge paths, and invariants surfaced while reviewing become `example_cases`, `edge_cases`, and `property_assertions`. L1 floors are met by construction, not by a separate brainstorming phase.
6. **Anti-bloat probes fire before every L0 create.** Run `forge find` for types, errors, constants. Present matches advisorily. Never silently create.
7. **Consistency probes are targeted, named, quiet when clean.** When a contradiction surfaces, cite the specific entity (`pol.X`, `atm.Y`, L1 section) and present options. Never narrate "I checked X, Y, Z" when no conflict exists.
8. **Partial spec: confirm+resume.** If fields exist from a prior session, acknowledge each, let the human correct, then continue from the first unfilled or uncertain field. Never wipe and restart unless explicitly asked.
9. **Within-module chain mode.** Stay in one session across atoms in the same module. `/clear` between modules, not between atoms.
10. **Stubs get filled, never recreated.** If an atom file already exists as a stub, you are completing it. You never write a new stub.

Full rationale: `references/framework.md §2`.

## Workflow

### Step 1 — Load context + classify review depth

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

**Review depth classification.** Read the stub's declared `side_effects`, the module context, and the atom's role in the module:

| Condition | Depth |
|---|---|
| Routine, sibling-pattern, low-risk atom | **D1 — Draft review** |
| Meaningful ambiguity, side effects with cross-entity implications, or likely L0/module cascades | **D2 — Draft + focused decisions** |
| Critical to module purpose, business correctness, security, data integrity, or `kind: MODEL` | **D3 — Draft + critical challenge** |

Ambiguous? Default to D2. Upgrade to D3 if criticality becomes clearer during review.

**Announce the depth:**
> *"I've drafted this atom first. Because it is `<reason>`, I'm using `<D1/D2/D3>` review depth."*

### Step 2 — Draft first, then review (sub-phase 1)

---

Always produce a best-effort draft before broad elicitation. If the context is too thin for a plausible draft, ask for one grounding example, then draft immediately — do not drift into open-ended field-by-field interrogation.

The draft should include:
- the full `spec` block
- initial verification items
- likely L0 additions
- likely module cascades

Present the review in five parts:
1. **Drafted spec**
2. **Assumptions made**
3. **Decision points**
4. **Conflicts or missing facts**
5. **Proposed L0 / module cascades**

#### D1 — Draft review

1. Draft from the strongest available pattern source (sibling atoms, caller expectations, module conventions).
2. Run anti-bloat and consistency probes silently during drafting. Any surfaced issue becomes a decision point or inline note in the draft.
3. Present: *"Here's the draft. What's wrong or missing?"*
4. Only open input or output contract questions if ambiguity or risk remains after the first review.
5. Revise once, then proceed to **Step 3 — Verification finalization**.

---

#### D2 — Draft + focused decisions (default)

1. Present the draft plus assumptions and decision points.
2. Ask targeted questions only where multiple valid choices exist or where the draft crosses ambiguity or caller risk.
3. Open input or output contract questions only when the contract is not confidently inferable or the choice affects downstream types, errors, or callers.
4. Run anti-bloat probes for each new L0 entity the draft still proposes.
5. Run consistency probes after the initial draft and again only for sections materially changed by the review.
6. Revise the spec, then present one compact second review pass.
7. Proceed to **Step 3 — Verification finalization**.

---

#### D3 — Draft + critical challenge

Start with the same draft-first review as D2. Then run structured challenge over the risk areas that matter for this atom:

1. **Business-critical correctness**
2. **Security / authorization**
3. **Data integrity / invariants**
4. **External failure handling**
5. **Caller / flow expectations**

For each area:
- ask only the unresolved decision points
- surface any named consistency conflicts
- revise the draft before moving to the next area

Open input or output contract questions here only when ambiguity or risk warrants them. Do not ask the human to enumerate fields from scratch if the draft is already directionally correct.

Proceed to **Step 3 — Verification finalization**.

---

### Step 3 — Verification finalization (sub-phase 2)

Check L1 verification floors: `min_property_assertions`, `min_edge_cases`, `min_example_cases`. These typically come from L1 `verification.floors`.

Verification should usually be mostly satisfied by the draft plus review cycle. Any examples, edge paths, or invariant statements surfaced while correcting the draft become verification items.

**If a floor is unmet:**
> *"L1 requires at least <N> <kind>. We have <M>. Give me one more — specifically, what happens when <suggested edge or failure path>?"*

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

## Review depth detail

Review depth selection happens at sub-phase 0 exit. Default to D2 unless the atom is clearly routine (D1) or clearly critical (D3).

**Upgrade rule:** if mid-review you discover the atom is genuinely more critical or more ambiguous than first assessed, upgrade D1 → D2 or D2 → D3. Announce the upgrade: *"This atom carries more risk than I first gauged — switching to D3 for the remaining review."* Do not downgrade once a deeper challenge has started.

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

- D1: all 7 checks silent during drafting; contradictions surface as inline notes or decision points in the draft
- D2: after the initial draft, and again only for sections materially changed by the human's decisions
- D3: after each challenge area, or whenever a decision changes the relevant section of the spec

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
- **Do not ask the human to rebuild the draft field-by-field.** If the draft is plausible, stay in review mode. Only open targeted input or output questions when ambiguity or risk remains.
- **Consistency probes are silent when clean.** Do not announce "I ran 7 consistency checks — all clear." That's narration for its own sake. Only speak up when a probe actually surfaces a conflict.
- **Never skip anti-bloat probes.** Even for obviously-novel types. The scan is cheap; the human sees it's genuinely novel and confirms quickly; that's the point.
- **Partial specs are the default, not an edge case.** Most elicitations hit sessions with some fields filled (the description was sharpened in sub-phase 0; decompose populated side_effects hints). Confirm+resume is the main path, not an exception.
- **If `forge context <atom>` returns exit 2 with unresolved refs**, the elicitation is not done. Either the refs are typos (fix them) or they point at atoms not yet elicited (add to `open_questions` and still commit — future elicitation sessions will catch them).
- **D1 requires high drafting confidence.** A sibling pattern helps, but is not mandatory. If the first review exposes broad uncertainty, upgrade to D2 rather than grinding through many corrections.
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
  - §3 review depth selection + flows
  - §4 L0 propagation tier policy
  - §5 anti-bloat probe templates
  - §6 consistency probe check classes
  - §7 sub-phase structure
  - §8 kind-specific spec shapes
  - §9 what forge-atom does NOT produce
  - §10 artifact schemas
- `assets/spec-review.template.md` — recommended structure for presenting drafted specs, decision points, and review outcomes
