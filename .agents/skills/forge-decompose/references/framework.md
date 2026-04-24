# forge-decompose — Framework

This document describes the **mental model** for `forge-decompose`: the stages, the question shapes, the extraction passes, the classification discipline, and the artifacts produced. It is **not** the SKILL.md; it is the source of truth from which any skill artifact is authored.

Audiences:
- An LLM or agent that executes the process
- An engineer authoring the `SKILL.md` from this framework
- A human facilitator running decompose without an AI

---

## 1. What `forge-decompose` is

**Purpose.** Take one module that has been bounded by `forge-discover` (identity + tech stack + dependency whitelist + empty `owned_atoms`) and produce an **exhaustive list of stubbed atoms** that live inside it. Write those stubs to disk, populate the module's `owned_atoms`, and stub any externally-triggered atoms' entry points.

**Scope contrast with `forge-discover`:**

| | discover | decompose |
|---|---|---|
| **Scope** | Whole system | One module at a time |
| **Input** | A vague idea | A bounded module + domain model from discover |
| **Output** | Scaffolding (modules, L0/L1/L5) | Atom stubs, populated `owned_atoms`, stub entry points, storage-neutral entity hints |
| **Work type** | Creative / exploratory | Analytical / extractive |
| **Interview feel** | Workshop | Depth interrogation |
| **Critical decisions** | Many (cloud, persistence, auth posture, etc.) | Few (one-atom-vs-two, ownership, kind disambiguation) |
| **Adaptation source** | Pains, comparisons, domain vocab | Module-specific verbs, sibling atoms, tech stack signals |

**Outputs at exit:**

| Artifact | Contains | Purpose |
|---|---|---|
| `L3_atoms/atm.<mod>.<name>.yaml` (one per atom) | `id`, `kind`, `owner_module`, `description`, empty `spec`, empty `verification`, one changelog entry | Discoverable stubs consumed by `forge-atom` |
| `L2_modules/<MOD>.yaml` (updated) | Populated `owned_atoms`, stub `interface.entry_points` (kind + invokes only) | Module's atom inventory + externally-triggered atom bindings |
| `supporting-docs/discovery-notes.md` (updated) | Classified candidate list, storage-neutral entity hints, `open_questions` for unresolved cross-module deps | Context for subsequent decompose and forge-atom sessions |

**What `forge-decompose` does NOT produce.** See §9.

---

## 2. Operating principles

Decompose inherits the full set from `forge-discover` — one concept per turn, concrete before abstract, extractive not generative, confirm by restating, scratchpad first, ground new questions in prior answers, resist premature naming, offer defaults explicitly, critical decisions get option sets. Full rationale in the discover framework §2.

**Principles specific to decompose:**

1. **Multi-pass exhaustiveness.** No single walkthrough reveals every atom. Never stop after one pass; the coverage comes from the layering of four deliberately overlapping passes (§6). Skipping a pass to save time guarantees gaps.
2. **Stubs only.** Decompose writes atom **stubs** — id, kind, owner_module, description. The `spec` block stays empty. Filling the spec is `forge-atom`'s job. Writing spec content at decompose time is premature commitment.
3. **Atomicity is editorial, not mechanical.** The atomicity rule (§8) is a prompt for judgment, not an automatic test. When a candidate violates the heuristic, the agent *probes* — it doesn't split automatically.
4. **Cross-module calls are noticed, flagged, verified — never resolved.** If decompose finds that an atom calls into another module, it records the reference and verifies the callee exists. It does not create atoms in the other module.
5. **Persistence hints stay storage-neutral.** When the walkthrough reveals a persisted entity, the hint captures the *entity concept* (`Charge`, `UserSession`), not the storage form (`tables`, `documents`, `key-value pairs`). Form is decided at forge-atom.

---

## 3. Decision criticality

Decompose has fewer critical decisions than discover. Only three decision types warrant **option-set treatment** (present 2–4 options with tradeoffs rather than defaulting):

| Decision | When it's critical |
|---|---|
| **One atom or two?** | When a candidate's description contains "and" joining two operations, or runs longer than one sentence |
| **Ownership** | When a candidate could plausibly belong to this module OR another in the dependency graph |
| **Kind classification** | When a candidate is borderline between two of the four kinds (e.g., config-loading PROCEDURAL vs. DECLARATIVE config) |

Everything else (naming, description wording, ordering of atoms in the list) is routine. Naming decisions happen *after* classification is settled, not before.

---

## 4. Adaptive questioning for decompose

Decompose inherits the `shape + content` model from discover. What changes is the **source of adaptation**: in discover, questions adapt to a growing domain model of users, pains, and vocabulary; in decompose, questions adapt to **module internals** — the verbs from this module's capability description, the atoms already named in this module, and the tech stack signals that hint at atom kind.

### Adaptation sources specific to decompose

- **Module verbs from the discovery domain model.** If discover recorded verbs like "reconcile" or "post" under this module's capability inventory, extraction questions use them: *"Walk me through one reconciliation end to end."* Not generic *"walk me through a use case."*
- **Sibling atoms as they get named.** Once a few atoms exist in this module's `owned_atoms`, subsequent questions reference them: *"You named `atm.pay.charge_card` earlier. Does this new candidate reuse any of that atom, or is it a peer?"* This surfaces duplication and relationship gaps.
- **Tech stack signals kind likelihood.** A module with `compute: lambda` has stateless-first semantics — the agent probes atoms for idempotency. A module with `managed_services: [aws-dynamodb]` suggests `form: key_value` for any persisted entities the module declares (hint only — confirmed at forge-atom). A module with prior COMPONENT atoms likely has more UI atoms coming.
- **Entry-point kinds signal atom kinds.** If the module has a `web_journey_entry` entry point, the atom it invokes is very likely a COMPONENT. If it has an `event_consumer` entry point, the atom is almost certainly PROCEDURAL.
- **Kind-specific probing tailors after first pick.** Once the agent picks PROCEDURAL for the first atom of a session, subsequent PROCEDURAL candidates skip the "what kind?" probe and go straight to atomicity check.

### Question shape reuse

Decompose draws from the same question shape taxonomy as discover (grounding, probing, boundary-finding, consistency-checking, scope-fencing, vocabulary-anchoring, prioritization, hypothetical, defaulting, option-set). See discover framework §4 for the full menu. Decompose leans predominantly on grounding, probing, consistency-checking, and option-set (for the three critical decisions above).

---

## 5. The four sub-phases

### Sub-phase 0 — Module grounding

**Purpose.** Load shared context with the human before asking anything structural.

**Entry trigger.** Skill invoked with or without a `<MOD>` argument.

**Actions:**
1. If no `<MOD>` argument, auto-select the most load-bearing unfilled module. Heuristic, in order:
   - First module listed in `supporting-docs/discovery-notes.md` `open_questions` (unresolved cross-module dep from a prior session)
   - The module tagged "hardest to get right" during discover sub-phase 1
   - First module alphabetically whose `owned_atoms` is empty
   
   Announce the auto-pick before proceeding; let the human redirect.

2. Run `forge inspect <MOD>` to load the current module state.
3. Read `supporting-docs/discovery-notes.md` — specifically the `capability_inventory`, `external_integrations_observed`, and the module's entries in the domain model (verbs, nouns, pains).
4. **Confirm with the human** that the module description is still accurate. If they want revisions, return to `forge-discover` with the revision hook; don't attempt to re-scope the module from within decompose.

**Writes.** Nothing new — context load only.

**Exit condition.** Human confirms the module's scope is still accurate.

---

### Sub-phase 1 — Multi-pass extraction

**Purpose.** Produce an exhaustive, *unclassified* candidate list. The bulk of decompose's interview time is spent here.

**Entry trigger.** Sub-phase 0 confirmed.

**Output target:** a growing `candidate_atoms_for_<MOD>` section in `supporting-docs/discovery-notes.md`, with each candidate tagged by which pass surfaced it.

Run the four passes in order. No pass can be skipped.

#### Pass 1 — Primary golden path

Walk the single most important use case this module handles end to end.

**Seed question (adapt using the module's capability inventory):**
> *"The most important thing [MOD] does is [capability from discover]. Walk me through one instance of that, start to finish — every step, including the ones that feel trivial."*

**Extraction rule:** every verb in the walkthrough is a candidate atom. Record them in the order they appear.

**Typical yield:** 50–70% of the final inventory.

#### Pass 2 — Alternate use cases

**Seed question:**
> *"What are 2 or 3 other ways [MOD] gets exercised? Admin paths, bulk operations, edge scenarios, different triggers."*

Walk each alternate end to end. New verbs merge into the list; duplicates from Pass 1 are noted but not re-added.

**Typical yield:** 15–25% more atoms beyond Pass 1 — the bulk/admin/edge atoms.

#### Pass 3 — Error paths and compensations

For each candidate so far, probe:

**Seed questions:**
- *"What fails in [candidate X]?"*
- *"When it fails, what undoes it or compensates?"*
- *"Are there recovery jobs — reconciliation, cleanup, retry-resolvers — that only exist to handle failures?"*

**Typical yield:** 5–15% more atoms — compensations, reconcilers, retry handlers.

#### Pass 2.5 — Cross-project duplicate scan (anti-bloat, advisory)

After passes 1–3 surface candidates but before pass 4's structural audits run, sweep the candidate list against the entire project's existing atoms to catch cross-module duplicates. For each candidate (or a keyword drawn from its label):

```bash
forge find <candidate_keyword> --kind atom --spec-dir <dir>
```

If any existing atom from *another* module shows up with meaningful overlap, present the match:

> *"Candidate `<candidate_label>` looks similar to existing atom `<existing_id>` in `<other_module>`:*
> *  `<existing_id>` — `<one-line description>` — match on `<signal>`*
> *Options:*
> *(a) Drop this candidate and let callers invoke `<existing_id>` directly (consolidate)*
> *(b) Move this candidate to `<other_module>` if it turns out to belong there (ownership fix)*
> *(c) Proceed — the two atoms have genuinely distinct responsibilities despite the name overlap*
> *Which fits?"*

Enforcement is **advisory**: the human can pick (c) without a written justification. The scan just ensures overlap is visible at the point where consolidation is cheapest.

**Typical yield:** not new atoms — removed or redirected ones. This pass's job is to *shrink* the candidate list where appropriate, not grow it.

#### Pass 4 — Coverage audits

The exhaustiveness insurance. Five structural sub-audits that catch gaps the human wouldn't name unprompted.

**4a. Data lifecycle audit.**
For each entity type the module will persist (from the entity hints surfaced across passes 1–3), iterate: *create / read / update / delete / search / aggregate*. Missing operations that the module clearly needs → candidate atoms.

*Gap signal:* a module that writes an entity but has no atom for "fetch by id" or "list by some key" probably has a read-path gap.

**4b. Side-effect coverage audit.**
For each relevant L0 `side_effect_marker`, ask: *does any atom in this module carry it?*

*Gap signals:*
- Module owns a datastore → at least one `WRITES_DB` atom expected
- Module's `access_permissions.external_schemas` is non-empty → at least one `CALLS_EXTERNAL` atom expected
- Module emits events (as declared in discover) → at least one `EMITS_EVENT` atom expected

Missing markers ≈ missing atoms.

**4c. Interface coverage audit.**
Every stub entry point in the module's `interface.entry_points` must invoke at least one atom. Walk the list and flag any that don't resolve yet.

**4d. Cross-module inbound audit.**
Scan the project — which *other* modules list this one in their `dependency_whitelist`? Those modules will call into this one. Probe: *"[Other module] has this one in its dep list. What atoms here does it expect to call?"* Reverse-lookup often reveals atoms that exist to serve other modules — often missed because the human walks outbound use cases, not inbound ones.

**4e. Maintenance / background audit.**
Explicit probe:
> *"Does this module do anything on a timer, or in response to system events unrelated to user actions? Scheduled jobs, migrations, cleanup tasks, health checks, monitoring probes?"*

These are the most commonly forgotten atoms — they're not in the "user clicks submit" mental model.

#### Pass outputs

After all four passes, `supporting-docs/discovery-notes.md` contains:

```yaml
candidate_atoms_for_<MOD>:
  - name:   <placeholder label>
    source: pass_1 | pass_2 | pass_3 | pass_4a | pass_4b | pass_4c | pass_4d | pass_4e
    description: <one-line summary from the walkthrough>
  # ...
```

**Exit condition for sub-phase 1:** all four passes run. The list is complete; classification is next.

---

### Sub-phase 2 — Review + classification (hybrid)

**Purpose.** Refine the candidate list through human review (broad), then classify each atom through focused dialogue (deep). Stub files written as each atom is classified.

#### Part A — Broad review

Agent presents the full candidate list from sub-phase 1. The human can:
- **Add** missing candidates the passes didn't surface
- **Remove** candidates that aren't really atoms (glue, overly fine-grained steps)
- **Merge** duplicates that appear under different labels
- **Split** candidates whose descriptions hint at multiple operations (probe with atomicity rule — §8)
- **Move** candidates that belong to a different module (ownership fix)

Agent's role in Part A: facilitator, not editor. Present the list clearly; make edits the human requests.

#### Part B — Deep classification (per atom, one at a time)

For each remaining candidate, walk through these probes *in order*:

1. **Atomicity probe** (§8 rule): *"Can this be described in one sentence without using 'and' to join operations? Can we write one standalone test case that exercises it independently?"* If either answer is no, option-set: *"Keep as one atom, or split into [proposed parts]?"*

2. **Ownership probe:** *"Does this atom belong to [MOD], or should it live in a different module?"* Option-set only if genuinely ambiguous.

3. **Triviality probe (anti-bloat, advisory, runs every atom).** Ask: *"What does this atom actually do beyond calling other atoms?"* If the answer is "nothing — it just forwards / wraps / delegates," present:

   > *"`<candidate>` looks like glue — its work is entirely `CALL <other_atom>` with some argument shaping. Options:*
   > *(a) Drop the atom; callers invoke the underlying atom directly with their own argument shaping.*
   > *(b) Keep it — it encapsulates a meaningful contract (e.g., it presents a simpler surface to callers, or multiple callers benefit from the shared shaping logic).*
   > *Which fits?"*
   
   Advisory only. The human may pick (b) without justification. The probe just makes sure glue-only atoms are a deliberate choice, not an accidental one.

4. **Per-atom duplicate scan (anti-bloat, advisory).** Before committing a name, run:

   ```bash
   forge find <candidate_keywords> --kind atom --spec-dir <dir>
   ```

   If Pass 2.5 already flagged this candidate, the human has already addressed it. Otherwise, if new matches surface now that classification has sharpened the candidate's meaning, present them:

   > *"Before naming `<proposed_id>`, I found existing atoms with overlapping names/descriptions:*
   > *- `<existing_id>` — `<one-line>`*
   > *Options: (a) merge into `<existing_id>` or move callers there, (b) refine this atom's description to sharpen the distinction, (c) proceed — the atoms are genuinely distinct.*
   > *Which?"*
   
   Advisory only. Just makes overlap visible at commit time.

5. **Kind probe:** Agent walks the four kinds with one-line distinguishers:
   - **PROCEDURAL** — takes input, does work, returns output. Covers handlers, functions, pipeline stages, event processors. The default.
   - **DECLARATIVE** — describes desired state, reconciled idempotently. Database schemas, infrastructure, config bundles.
   - **COMPONENT** — renders UI, holds local state, emits events. Screens, widgets, CLI TUI elements.
   - **MODEL** — probabilistic output with acceptable bounds. Classifiers, prediction models, heuristic matchers.
   
   Ask: *"Which fits?"* If borderline (e.g., PROCEDURAL vs DECLARATIVE), present option-set explicitly.

6. **Naming:** Once classification is locked, commit a name following `L0.naming_ledger.atom_id`. Typical pattern: `atm.<3-letter-module>.<snake_case_verb>`.

7. **Write stub file immediately** at `<spec-dir>/L3_atoms/atm.<mod>.<name>.yaml` using the `assets/atom-stub.template.yaml` shape:

```yaml
atom:
  id:           <atm.mod.name>
  kind:         <PROCEDURAL | DECLARATIVE | COMPONENT | MODEL>
  owner_module: <MOD>
  description: |
    <one or two sentences describing what this atom does — not how>

  spec: {}              # populated by forge-atom

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

8. **Refresh sibling context.** Before moving to the next atom, the agent re-reads the growing `owned_atoms` list so subsequent questions can reference the just-named atom.

**Exit condition for sub-phase 2:** every candidate from sub-phase 1 is either stubbed, explicitly dropped (with rationale in notes), or moved to another module's candidate list.

---

### Sub-phase 3 — Module + entry-point finalization

**Purpose.** Wire everything together. Update the module file, write entry-point stubs, capture persistence hints, verify cross-module calls.

**Actions:**

1. **Update `L2_modules/<MOD>.yaml`:** set `owned_atoms` to match the classified list.

2. **Write stub entry points** for externally-triggered atoms:
   - Walk the atom list; for each atom whose walkthrough indicated external triggering (api endpoint, event, schedule, etc.), add an entry-point stub:
     ```yaml
     interface:
       entry_points:
         - kind:    <api | event_consumer | cli | scheduled | websocket | grpc | web_journey_entry | mobile_journey_entry>
           invokes: <atom_id>
           # endpoint / method / event / schedule / types / security — filled by forge-atom
     ```
   - The `kind` and `invokes` fields are both knowable from the walkthrough. Everything else is deferred.

3. **Write storage-neutral entity hints** to `supporting-docs/discovery-notes.md`:
   ```yaml
   likely_persisted_entities_for_<MOD>:
     - entity_concept: <logical entity name — e.g., Charge, UserSession>
       written_by:     <atom_id>
       read_by:        [<atom_ids>]
       likely_keys:    [<field names suggesting access patterns>]
       # storage form (relational/document/key_value/etc.) decided at forge-atom
   ```

4. **Verify cross-module calls.** For each atom whose description mentions calling into another module (e.g., `atm.pay.charge_card` calls `atm.usr.fetch_customer`):
   - Run `forge inspect <called-atom>` to check existence.
   - If exists: record the dependency in `supporting-docs/discovery-notes.md`.
   - If not: add to `open_questions` as an unresolved dependency (e.g., *"atm.pay.charge_card references atm.usr.fetch_customer which does not exist; decompose USR to resolve"*).
   - **Never create atoms in another module from this decompose session.**

5. **Run `forge list --spec-dir <dir>`** and confirm every new atom appears as discoverable.

6. **Handover with dual-path surfacing.** The skill detects the broader project state and presents *both* meaningful next steps, recommending a default:

   **a. Detect remaining unfilled modules.** Walk all modules and find those whose `owned_atoms` is still empty.
   
   **b. Compute both next-step candidates:**
   - The next module that would be auto-picked if `/forge-decompose` runs again (same heuristic as Step 1: open_questions → hardest-to-get-right → alphabetical)
   - The atom in the just-decomposed module most worth eliciting first (most downstream callers → hardest-to-get-right → alphabetical)
   
   **c. Present both paths** with a recommended default:
   
   - When **unfilled modules remain:** recommend **continue decomposing** as Option 1. Breadth-first through the project, one module per session with `/clear` between. Offer forge-atom as Option 2.
   - When **all modules are decomposed:** recommend starting forge-atom on the most load-bearing atom.
   
   **d. Make the `/clear` + `/forge-decompose` loop explicit** in the handover message, so the 2-keystroke workflow becomes muscle memory.

**Why "continue decomposing" is the recommended default** when modules remain:

- Decompose is fast (stubs only); forge-atom is slow (full specs per atom). Finishing decompose across the project before switching modes preserves momentum.
- Cross-module gaps surface earlier with breadth-first decomposition. If module B's walkthrough reveals an atom that module A should own, catching that during A's decompose is much cheaper than during B's forge-atom.
- The `/clear` is a natural save point — state is already on disk, nothing is lost, and the next invocation resumes via auto-pick without the human tracking where they left off.

**Exit condition for sub-phase 3:**
- Module's `owned_atoms` matches the stubbed atom list
- Every stub entry point has a non-null `invokes`
- Every cross-module call is either verified or flagged
- `forge list` shows all new atoms

---

## 6. Exhaustiveness analysis — why multi-pass works

The four-pass structure achieves coverage across four orthogonal kinds of "what atoms might exist":

| Pass | Coverage kind | What it catches |
|---|---|---|
| 1 | **Semantic (primary)** | What the module *does* in the main use case — the obvious atoms |
| 2 | **Semantic (breadth)** | Other ways the module is used — bulk / admin / edge paths |
| 3 | **Behavioral** | What happens when things break — compensations, reconcilers, retry handlers |
| 4a | **Structural (data)** | Missing CRUD/search/aggregate operations for persisted entities |
| 4b | **Structural (effects)** | Atoms implied by the module's side-effect surface |
| 4c | **Structural (interfaces)** | Atoms required by declared entry points |
| 4d | **Interaction** | Atoms required by inbound calls from other modules |
| 4e | **Operational** | The invisible-infrastructure atoms — timers, jobs, health checks |

A module can hide atoms in exactly one place after all four passes complete: **human knowledge not surfaced by any probe.** That residual is what `forge-audit` (skill 4) catches later. The multi-pass extraction gets us ~95% of the way there; audit closes the remaining gap.

---

## 7. Classification discipline

Four kinds, three probes per atom. The kind picks lock the spec block shape forge-atom will fill.

### Kind distinguishers (agent presents during kind probe)

- **PROCEDURAL** — Input → work → output. Side effects optional. Default for functions, handlers, processors, logic paths. If an atom "does a thing and returns something," it's PROCEDURAL.
- **DECLARATIVE** — Describes a target desired state; reconciliation brings the system to that state idempotently. Database migrations, infrastructure-as-code, config files, CSS definitions. If an atom "is" rather than "does," it's DECLARATIVE.
- **COMPONENT** — Renders UI, holds local state, emits events. Props in, rendered tree + event stream out. If an atom is a screen, widget, or TUI element, it's COMPONENT.
- **MODEL** — Probabilistic output with declared acceptable bounds. Classifiers, prediction models, fuzzy matchers, anything where the "correct" output is a distribution rather than a value. If an atom "guesses" with confidence, it's MODEL.

### Edge cases (present as option-set when encountered)

| Candidate description | Borderline between | How to resolve |
|---|---|---|
| "Loads config and validates it at startup" | PROCEDURAL vs DECLARATIVE | If the atom's job is *to declare the config state*, DECLARATIVE. If the atom's job is *to process a config file as input*, PROCEDURAL. |
| "Renders a server-side HTML page" | PROCEDURAL vs COMPONENT | COMPONENT in frameworks that track local state + emit events; PROCEDURAL if it's a pure function of input → HTML with no lifecycle. |
| "Heuristic matching with fallback to exact lookup" | MODEL vs PROCEDURAL | MODEL if there are acceptable_bounds (false-positive rate, recall); PROCEDURAL if the heuristic is deterministic. |
| "Database schema migration" | DECLARATIVE vs PROCEDURAL | DECLARATIVE if it declares the target state; PROCEDURAL if it runs a sequence of imperative steps. |

---

## 8. Atomicity stopping rule

The rule used during the classification's atomicity probe (sub-phase 2 Part B step 1).

**Primary rule:** *the atom's description fits in one sentence without using "and" to join distinct operations.*

**Secondary verification:** *we can write one standalone test case — concrete input, concrete expected output/effect, independently verifiable.*

**When the rule is violated**, the agent does not automatically split. It presents an option set:

> *"This candidate's description contains 'and' joining two operations — `validate` and `persist`. Two possibilities:*
> *1. **Keep as one atom** — if the two operations are genuinely a single transaction that can't meaningfully happen separately (e.g., validate-then-persist is atomic at the DB level).*
> *2. **Split into two atoms** — `atm.pay.validate_charge` and `atm.pay.persist_charge` — if they can be tested and composed independently.*
> *Which fits?"*

**Escape valve:** if the description runs longer than ~2 sentences regardless of "and" count, the agent flags it as likely over-broad and probes for splits.

The atomicity rule is editorial, not mechanical — a prompt for judgment. Legitimate atomic operations with multiple side effects exist (e.g., "charge the card and emit payment.completed" is one atom because the emission is tied to the charge's success in a single transaction).

---

## 9. What `forge-decompose` does NOT produce

The discipline that keeps the pipeline clean:

| Not produced at decompose | Deferred to |
|---|---|
| L0 types (atom input/output shapes) | `forge-atom` when the atom's spec forces them |
| L0 errors (per-atom failure codes) | `forge-atom` when the atom's `failure_modes` are specified |
| L0 constants | `forge-atom` when logic references them |
| Atom `spec` blocks (full specs) | `forge-atom` — that's its entire purpose |
| `persistence_schema.datastores` entries in module files | `forge-atom` when the atom's `side_effects` and output type force the form |
| `access_permissions` expansions (env_vars, secrets, network) | `forge-atom` when the atom declares what it needs |
| Policies | When a sensitive atom exists and forge-atom surfaces the need |
| L4 flows / journeys | `forge-compose` |

The enforced discipline: **decompose produces stubs, not specs.** Stubs are discoverable; specs require the deep contract detail only forge-atom extracts.

---

## 10. Artifact schemas

### Candidate list — `supporting-docs/discovery-notes.md` addendum

```yaml
candidate_atoms_for_<MOD>:
  - name:        <placeholder or committed id>
    source:      pass_1 | pass_2 | pass_3 | pass_4a | pass_4b | pass_4c | pass_4d | pass_4e
    description: <one-line summary>
    status:      pending_review | pending_classification | stubbed | dropped | moved_to_<other_mod>
    # filled progressively as sub-phase 2 runs:
    kind:        PROCEDURAL | DECLARATIVE | COMPONENT | MODEL
    committed_id: atm.<mod>.<name>
    stub_file:   L3_atoms/atm.<mod>.<name>.yaml
```

### Entity hints — `supporting-docs/discovery-notes.md` addendum

```yaml
likely_persisted_entities_for_<MOD>:
  - entity_concept: <logical name, e.g., Charge>
    written_by:     <atom_id>
    read_by:        [<atom_ids>]
    likely_keys:    [<field names suggesting access patterns>]
    # form decided at forge-atom
```

### Open questions — `supporting-docs/discovery-notes.md` addendum

```yaml
open_questions:
  - summary:      "atm.pay.charge_card references atm.usr.fetch_customer which does not exist"
    kind:         unresolved_cross_module_call
    blocking:     false   # true if decompose cannot finish without resolution
    recommended:  "Run /forge-decompose USR to produce fetch_customer stub"
```

### Atom stub — `L3_atoms/atm.<mod>.<name>.yaml`

See `assets/atom-stub.template.yaml`.

### Module update shape

The `L2_modules/<MOD>.yaml` file's fields that decompose writes:

```yaml
module:
  # (unchanged from discover): id, name, description, tech_stack, persistence_schema, dependency_whitelist, ...
  owned_atoms:
    - atm.<mod>.<name_1>
    - atm.<mod>.<name_2>
    # ...
  interface:
    entry_points:
      - kind:    <kind>
        invokes: <atom_id>
        # path/method/types/security — deferred to forge-atom
  changelog:
    # append new entry:
    - version:     <next_version>
      date:        <YYYY-MM-DD>
      change_type: modified
      description: "Populated owned_atoms and stub entry points via forge-decompose."
```

---

## 11. Compatibility with skill formats

Same as forge-discover: the framework is format-agnostic. The skill artifact at `.agents/skills/forge-decompose/SKILL.md` references this framework under `references/framework.md` for progressive disclosure — load on demand when the agent needs to look up the exhaustiveness analysis (§6), kind edge cases (§7), or the atomicity rule rationale (§8).

---

## 12. Open design questions (for future iteration)

- **Should decompose handle atom consolidation?** If the candidate list has near-duplicates ("save_order" + "persist_order"), should the agent flag them for merge? Current design leaves this to the human during Part A review, but a semantic-similarity pass could help.
- **When should atomicity be re-checked?** If forge-atom later reveals an atom has complex branching logic, does that signal a late-stage split? Currently handled by `forge-audit`.
- **Multi-module decomposition in one session?** If a cross-module call surfaces a missing callee in another module, should the skill offer to jump into that module? Current design says no (scope creep); a future version could offer an explicit cross-module hop.
