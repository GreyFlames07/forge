---
name: forge-decompose
description: >
  Use this skill when a user needs to break a bounded Forge module into
  its atom inventory — i.e., the module exists in L2_modules/ with identity,
  tech_stack, and dependency_whitelist set, but owned_atoms is empty or
  sparse. Activates on phrases like "decompose this module", "what atoms
  belong in X", "break down the module", "let's find the atoms in", or when
  forge list shows one or more modules with empty owned_atoms. Drives a
  four-pass extraction followed by hybrid review+classification, producing
  stub atom files, populated owned_atoms, stub entry points (kind+invokes
  only), and storage-neutral entity hints. Does NOT produce L0 types,
  errors, constants, full atom specs, persistence_schema entries, or
  policies — those are forge-atom's job.
---

# forge-decompose

Take one bounded Forge module and produce an exhaustive, classified inventory of stubbed atoms. You ask questions in a structured four-pass extraction, then classify each candidate one-by-one and write stub files as you go. You produce atom stubs (id + kind + owner_module + description + empty spec), populated `owned_atoms`, stub entry points, and storage-neutral persistence hints. You do NOT write full atom specs — that's `forge-atom`'s job.

Full mental model, exhaustiveness rationale, kind edge cases, and artifact schemas are in `references/framework.md` (~700 lines). Load on demand:
- `§5` for per-sub-phase deep guidance
- `§6` for why the four-pass structure converges on exhaustive
- `§7` for kind-classification edge cases when a candidate is borderline
- `§8` for the atomicity-rule rationale
- `§10` for exact artifact schemas

Otherwise this file is self-sufficient for routine operation.

## Non-negotiables

1. **Batch within extraction passes; sequence across passes.** Within a pass, group related capability questions together — the human can scan and answer a coherent set faster than waiting for single drips. Across passes, stay sequential — each pass is designed to catch what the previous missed. Critical decisions (one-vs-two atoms, module ownership, borderline kind classification) always get their own single turn as an option-set.
2. **Stubs only.** The `spec` block of every atom file stays empty. Do not write input/output/logic/invariants/failure_modes — those are forge-atom's job. Writing them at decompose is premature commitment.
3. **All four extraction passes.** Sub-phase 1 runs Pass 1 → 2 → 3 → 4. Skipping a pass guarantees atom gaps. Each pass catches atoms the others hide.
4. **Atomicity is editorial.** When a candidate violates the atomicity rule, PROBE with an option-set; do not automatically split. The human decides.
5. **Cross-module calls: notice, flag, verify — never resolve.** Run `forge inspect <called-atom>` to check existence. If missing, record in `open_questions`. Never create atoms in another module from this session.
6. **Persistence hints stay storage-neutral.** Capture entity-concept level (`Charge`, `Session`) — never `tables`, `documents`, `key-value pairs`. Storage form is decided at forge-atom.
7. **Write stub files as you classify** — not in a batch at the end. Each classified atom → one file write immediately.
8. **Critical decisions get option sets.** Three decisions warrant this: one-atom-vs-two, ownership between modules, borderline kind classification. Present 2–4 options; never silently pick.

Full rationale: `references/framework.md §2`.

## Workflow

### Step 1 — Load context

```bash
forge list --spec-dir <spec-dir>           # see all modules, find unfilled ones
forge inspect <MOD> --spec-dir <spec-dir>  # load target module state
```

If invoked as `/forge-decompose <MOD>`, use that argument.

If invoked as `/forge-decompose` (no argument), auto-select the most load-bearing unfilled module. Heuristic, in order:
1. First module listed in `supporting-docs/discovery-notes.md` `open_questions` (unresolved cross-module dep from a prior session)
2. The module tagged "hardest to get right" during discover sub-phase 1
3. First module alphabetically whose `owned_atoms` is empty

Announce the auto-pick before proceeding. Example:

> *"Auto-selected `PAY` as most load-bearing — it was flagged as hardest to get right in discover. Continue, or pick a different module?"*

Read `supporting-docs/discovery-notes.md` for domain model, capability inventory, and any relevant `open_questions` that reference this module. These shape your questions.

### Step 2 — Run sub-phases 0 → 3

---

#### Sub-phase 0 — Module grounding

Confirm with the human that the module's current description (from `forge inspect <MOD>`) is still accurate. If they want to revise the module's scope or boundary, return them to `forge-discover` — do NOT attempt to re-scope from within decompose.

**Exit when:** human confirms the module description is still accurate for decomposition.

---

#### Sub-phase 1 — Multi-pass extraction

Create a `candidate_atoms_for_<MOD>` section in `supporting-docs/discovery-notes.md` using the structure in `assets/candidates.template.md`. Every atom surfaced below goes into this list, tagged with which pass surfaced it.

Run all four passes in order. Do not skip. Exhaustiveness depends on the layering — see `references/framework.md §6`.

**Pass 1 — Primary golden path.**

Ask: *"The most important thing `<MOD>` does is [capability from discover]. Walk me through one instance of that, start to finish — every step, including the ones that feel trivial."*

Every verb the human uses is a candidate atom. Record in order with `source: pass_1`.

**Pass 2 — Alternate use cases.**

Ask: *"What are 2 or 3 other ways `<MOD>` gets exercised? Admin paths, bulk operations, edge scenarios, different triggers."*

Walk each alternate. Merge new verbs into the candidate list with `source: pass_2`. Duplicates from Pass 1 are noted but not re-added.

**Pass 3 — Error paths and compensations.**

For each candidate surfaced so far:
- *"What fails in [candidate]?"*
- *"When it fails, what undoes it or compensates?"*
- *"Are there recovery jobs — reconciliation, cleanup, retry-resolvers — that only exist to handle failures?"*

New candidates get `source: pass_3`.

**Pass 4 — Coverage audits (mechanical sweep).**

Five sub-audits. Each surfaces *structural* atom gaps the human wouldn't name unprompted. Run all five:

- **4a. Data lifecycle.** For each entity concept the module will persist (from hints surfaced in passes 1–3), iterate CRUD + search + aggregate. Missing operations that the module clearly needs → candidates with `source: pass_4a`.

- **4b. Side-effect coverage.** For each relevant L0 side-effect marker, ask: does any atom in this module carry it? Gaps = candidates. Key markers to check: `WRITES_DB`, `EMITS_EVENT`, `CALLS_EXTERNAL`, `READS_CACHE`, `READS_ARTIFACT`, `READS_CLOCK`.

- **4c. Interface coverage.** Every stub entry point in the module's `interface.entry_points` must invoke at least one atom. Walk the list; any that don't resolve yet are gaps.

- **4d. Cross-module inbound.** Scan the project — which *other* modules list this one in their `dependency_whitelist`? For each, ask: *"What atoms here does `<other-MOD>` expect to call?"* Inbound-driven atoms are often missed.

- **4e. Maintenance / background.** Explicit probe: *"Does `<MOD>` do anything on a timer, or in response to system events unrelated to user actions? Scheduled jobs, migrations, cleanup tasks, health checks, monitoring probes?"*

**Pass 2.5 — Cross-project duplicate scan (anti-bloat, advisory; runs between Pass 2 and Pass 3 or after Pass 3).**

For each candidate surfaced so far, scan the project's existing atoms for overlap:

```bash
forge find <candidate_keyword> --kind atom --spec-dir <dir>
```

If any existing atom from *another* module shows up with meaningful overlap (same verb, similar description), present the match:

> *"Candidate `<candidate>` looks similar to existing atom `<existing_id>` in `<other_module>`:*
> *- `<existing_id>` — `<one-line>`*
> *Options:*
> *(a) Drop this candidate; callers invoke `<existing_id>` directly*
> *(b) Move this candidate to `<other_module>` if it belongs there*
> *(c) Proceed — genuinely distinct despite the overlap*
> *Which?"*

Advisory — human may pick (c) without justification. This pass shrinks the candidate list where appropriate; it does not add atoms.

**Exit when:** all four passes plus the duplicate-scan pass have run. The candidate list is complete (pending human review).

---

#### Sub-phase 2 — Review + classification (hybrid)

Two parts: broad review (human edits the list) then deep classification (agent walks each atom one-by-one).

**Part A — Broad review.**

Present the full candidate list clearly, grouped by source pass. The human can:
- **Add** missing candidates
- **Remove** candidates that aren't really atoms (glue, too-fine-grained)
- **Merge** duplicates appearing under different labels
- **Split** candidates with multi-operation descriptions
- **Move** candidates that belong to a different module (mark `status: moved_to_<MOD>`)

Your role in Part A: facilitator. Present the list; make the edits the human requests. Do not editorialize.

**Part B — Deep classification (per atom).**

For each remaining candidate, walk these probes *in order*, one atom at a time:

1. **Atomicity probe.** Rule: *one sentence without "and" joining distinct operations, AND we can write one standalone test case.*
   - If the rule holds → proceed.
   - If violated → present option-set:
     > *"This candidate's description contains 'and' joining two operations — `[op1]` and `[op2]`. Two possibilities:*
     > *1. Keep as one atom — if the two operations are genuinely a single transaction (e.g., validate-then-persist is atomic at the DB level).*
     > *2. Split into `[atom-a]` and `[atom-b]` — if they can be tested and composed independently.*
     > *Which fits?"*

2. **Ownership probe.** *"Does this atom belong to `<MOD>`, or should it live in a different module?"* Option-set only if genuinely ambiguous.

3. **Triviality probe (anti-bloat, advisory, runs every atom).** Ask the human: *"What does this atom actually do beyond calling other atoms?"* If the answer is essentially "nothing — it forwards / wraps / delegates," present:

   > *"`<candidate>` looks like glue — its work is mostly `CALL <other_atom>` with argument shaping. Options:*
   > *(a) Drop the atom; callers invoke the underlying atom directly*
   > *(b) Keep it — it encapsulates a meaningful contract (simpler surface for callers, or multiple callers share the shaping logic)*
   > *Which?"*
   
   Advisory only. Human may pick (b) without justification. This makes glue-only atoms a deliberate choice rather than an accidental one.

4. **Per-atom duplicate scan (anti-bloat, advisory).** Before committing a name, run:

   ```bash
   forge find <candidate_keyword> --kind atom --spec-dir <dir>
   ```
   
   Skip if Pass 2.5 already surfaced and addressed this candidate's duplicates. Otherwise, if new matches appear now that classification has sharpened the candidate's meaning, present them:
   
   > *"Before naming `<proposed_id>`, I found existing atoms with overlapping names/descriptions:*
   > *- `<existing_id>` — `<one-line>`*
   > *Options: (a) merge into `<existing_id>` or move callers there, (b) refine this atom's description to sharpen the distinction, (c) proceed — genuinely distinct.*
   > *Which?"*
   
   Advisory only.

5. **Kind probe.** Present the four kinds with distinguishers:
   - **PROCEDURAL** — takes input, does work, returns output. Default for functions, handlers, processors. "Does a thing and returns something."
   - **DECLARATIVE** — describes desired state; reconciled idempotently. Database schemas, infrastructure, config. "Is rather than does."
   - **COMPONENT** — renders UI, holds local state, emits events. Screens, widgets, TUI elements.
   - **MODEL** — probabilistic output with acceptable bounds. Classifiers, predictors, fuzzy matchers.
   
   Ask: *"Which fits?"* If borderline, present a narrower option-set. See `references/framework.md §7` for edge-case guidance (config loaders, SSR pages, heuristic matchers, DB migrations).

6. **Name the atom** following `L0.naming_ledger.atom_id` — typically `atm.<3-letter-module>.<snake_case_verb>`. Commit only after classification is locked.

7. **Write the stub file immediately** at `<spec-dir>/L3_atoms/atm.<mod>.<name>.yaml` using the structure from `assets/atom-stub.template.yaml`:

```yaml
atom:
  id:           <atm.mod.name>
  kind:         <PROCEDURAL | DECLARATIVE | COMPONENT | MODEL>
  owner_module: <MOD>
  description: |
    <one or two sentences describing what this atom does — not how>

  spec: {}                      # populated by forge-atom

  verification:
    property_assertions: []
    example_cases:       []
    edge_cases:          []

  convention_overrides: []
  policy_overrides:     []

  changelog:
    - version:     "0.1.0"
      date:        <YYYY-MM-DD>
      change_type: added
      description: "Stub created by forge-decompose."
```

8. **Update the candidate's `status` to `stubbed`** in the running list in `supporting-docs/discovery-notes.md`. Record the `committed_id` and `stub_file` path.

9. **Move to the next candidate.** Re-read the growing `owned_atoms` list so subsequent questions can reference just-named atoms.

**Exit when:** every candidate is either `stubbed`, `dropped` (with rationale), or `moved_to_<MOD>`.

---

#### Sub-phase 3 — Module + entry-point finalization

Four actions:

1. **Populate `owned_atoms`** in `<spec-dir>/L2_modules/<MOD>.yaml`:
   ```yaml
   owned_atoms:
     - atm.<mod>.<name_1>
     - atm.<mod>.<name_2>
     # ...
   ```

2. **Write stub entry points** for externally-triggered atoms:
   ```yaml
   interface:
     entry_points:
       - kind:    <api | event_consumer | cli | scheduled | websocket | grpc | web_journey_entry | mobile_journey_entry>
         invokes: <atom_id>
         # endpoint / method / event / schedule / types / security — filled by forge-atom
   ```
   
   `kind` and `invokes` are knowable from the walkthrough. Everything else is deferred.

3. **Capture storage-neutral entity hints** in `supporting-docs/discovery-notes.md`:
   ```yaml
   likely_persisted_entities_for_<MOD>:
     - entity_concept: <logical name, e.g., Charge>
       written_by:     <atom_id>
       read_by:        [<atom_ids>]
       likely_keys:    [<field names>]
       # form decided at forge-atom
   ```

4. **Verify cross-module calls.** For each atom whose description references calling into another module:
   ```bash
   forge inspect <called-atom> --spec-dir <spec-dir>
   ```
   - If exists: record dependency in the candidate's notes.
   - If missing: add to `open_questions` in `supporting-docs/discovery-notes.md` with `kind: unresolved_cross_module_call`.
   - **Never create atoms in another module from this session.**

5. **Verify discoverability.** Run:
   ```bash
   forge list --kind atom --spec-dir <spec-dir>
   ```
   Every new stubbed atom should appear. If any don't, check the file path and naming regex.

6. **Append module changelog entry:**
   ```yaml
   changelog:
     - version:     <next>
       date:        <YYYY-MM-DD>
       change_type: modified
       description: "Populated owned_atoms and stub entry points via forge-decompose."
   ```

### Step 3 — Handover

Compute the handover state in three steps.

**1. Summarize what was done:**
- N atoms stubbed, broken down by kind (e.g., 8 PROCEDURAL, 1 DECLARATIVE, 2 COMPONENT)
- M stub entry points
- K cross-module dependencies flagged (list them)
- Any `open_questions` added

**2. Detect remaining unfilled modules** (modules whose `owned_atoms` is still empty):

```bash
# For each module, check if it has any owned atoms.
forge list --kind module --ids-only --spec-dir <spec-dir> | while read m; do
  owned=$(forge inspect "$m" --spec-dir <spec-dir> | grep -c '^- atm\.')
  [ "$owned" -eq 0 ] && echo "$m"
done
```

**3. Present the handover with both paths surfaced.**

The two paths:
- **Continue decomposing modules** — breadth-first through the project, one module per session with `/clear` between. Recommended default when unfilled modules remain.
- **Start deepening this module's atom specs** — switch to `forge-atom` now. Recommended when all modules are decomposed, or when the human explicitly wants to go deep on this module first.

**Case A — one or more unfilled modules remain:**

> *"`<MOD>` decomposed — `N` atoms stubbed (`<breakdown by kind>`).*
> *`K` cross-module dependencies flagged, `Q` open questions added.*
> 
> *`R` modules still need decomposing: `<list>`.*
> 
> **Option 1 (recommended) — continue decomposing with fresh context.**
> *Next auto-pick: `<next_mod>` (reason: `<open_question | hardest-to-get-right | alphabetical>`).*
> *To continue:*
> *1. Type `/clear`*
> *2. Type `/forge-decompose` (I'll auto-pick `<next_mod>`)*
> 
> **Option 2 — start deepening atom specs for `<MOD>`.**
> *I'd recommend starting with `<atom_id>` — `<most downstream callers | flagged hardest-to-get-right>`.*
> *Run `/forge-atom <atom_id>`.*
> 
> *Which path?"*

**Case B — all modules now have atoms:**

> *"`<MOD>` decomposed — `N` atoms stubbed (`<breakdown>`).*
> 
> *All project modules now have atom inventories. Ready to start eliciting specs.*
> 
> *I'd recommend starting with `<atom_id>` — `<most downstream callers | flagged hardest-to-get-right>`.*
> *Run `/forge-atom <atom_id>`."*

### Handover heuristics

**Next module to decompose** (same as Step 1 auto-pick):
1. First module in `supporting-docs/discovery-notes.md` `open_questions` (unresolved cross-module dep)
2. The module tagged "hardest to get right" during discover sub-phase 1
3. First module alphabetically whose `owned_atoms` is empty

**Next atom to elicit** (within the just-decomposed module):
1. The atom with the most *other atoms* referencing it in their descriptions (most downstream reliance)
2. The atom covering the capability tagged "hardest to get right" during discover
3. The first atom alphabetically

## Critical decisions — option-set protocol

Three decision types where you MUST present options instead of silently picking:

1. **One atom or two?** (atomicity-rule violation)
2. **Ownership** (between this module and another)
3. **Kind classification** (borderline between two kinds)

Option-set template:

```
[Restate the candidate and the ambiguity.]

Your options:

1. **[Option A]** — [one-line benefit]. [one-line tradeoff]. Best when [context].
2. **[Option B]** — [one-line benefit]. [one-line tradeoff]. Best when [context].

Which fits?
```

Full rationale: `references/framework.md §3` (criticality in decompose) and `§7` (kind edge cases).

## Adaptation rules

- **Use verbs from the module's capability inventory** in discover's `supporting-docs/discovery-notes.md`. Don't say "walk me through a use case"; say "walk me through one `<verb>` end to end" using the verb the human introduced.
- **Reference sibling atoms as they get named.** After the second atom is stubbed, questions about subsequent candidates can say: *"You already named `atm.<mod>.<prior>`. Does this reuse any of it, or is it a peer?"*
- **Tech stack signals kind likelihood.** When the module has `compute: lambda`, probe statelessness for PROCEDURAL candidates. When `managed_services` includes a document/KV store, bias hints toward non-relational when entity hints emerge. When the module already has COMPONENT atoms, expect more.
- **Entry-point kinds signal atom kinds.** `web_journey_entry` → almost certainly COMPONENT. `event_consumer` → almost certainly PROCEDURAL. Let the entry-point kind shape the kind probe.
- **After the first kind is picked in a session**, skip the four-kind walk for subsequent candidates of the same kind. Go straight to atomicity.

## Gotchas

- **Do not skip any of the four passes.** Exhaustiveness depends on the layering. Pass 4d (cross-module inbound) is the most commonly skipped and the most commonly productive — always run it.
- **Pass 4c uses the stub entry points you just created in sub-phase 0's loaded state.** If the module already had entry points before decompose, those are inputs; if not, you'll need to create them in sub-phase 3 after atoms exist.
- **Never write anything in the `spec:` block of a stub file.** Leaving it as `{}` is correct. Elicit-atom fills it.
- **Never create atoms in another module.** If pass 4d reveals that another module needs an atom, record it in that module's future decompose session — not this one.
- **The atomicity rule is not an automatic split trigger.** "Validate and persist" can legitimately be one atom if they're an atomic transaction. Always probe with option-set.
- **If the `forge` CLI is unavailable**, read YAML files directly. The protocol is identical; the CLI is just a convenient accessor.
- **Silence is not agreement.** If the human doesn't respond to a critical-decision option-set, ask explicitly: *"Going with option 1, or a different direction?"*
- **If the walker's forge list output doesn't show a new atom after stubbing**, the atom ID probably doesn't match the L0 `naming_ledger.atom_id` regex. Check it.

## forge CLI commands used by this skill

| Command | Used for |
|---|---|
| `forge list --spec-dir <dir>` | Overall state check at entry; find modules with empty `owned_atoms` for auto-pick heuristic |
| `forge inspect <MOD> --spec-dir <dir>` | Load the target module's current state in sub-phase 0 |
| `forge inspect <called-atom> --spec-dir <dir>` | Verify cross-module calls in sub-phase 3 |
| `forge list --kind atom --spec-dir <dir>` | Confirm new stubbed atoms are discoverable at end of sub-phase 3 |
| `forge list --kind module --ids-only --spec-dir <dir>` | Pipe-ready module ID list when auto-picking across many modules |

## References

- `references/framework.md` — full mental model. Sections:
  - §2 operating principles rationale
  - §3 decision criticality in decompose
  - §4 adaptive questioning sources
  - §5 per-sub-phase deep guidance
  - §6 exhaustiveness analysis (why four passes converge)
  - §7 kind-classification edge cases
  - §8 atomicity-rule rationale
  - §9 what decompose does NOT produce
  - §10 artifact schemas
- `assets/atom-stub.template.yaml` — canonical stub shape
- `assets/candidates.template.md` — candidate list structure for `supporting-docs/discovery-notes.md`
