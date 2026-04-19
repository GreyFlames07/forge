---
name: forge-discover
description: >
  Use this skill when a user is starting a new software project, has an
  early-stage product idea to workshop, or needs to establish the top-level
  structure of a Forge-framework project — modules, vocabulary baseline,
  project conventions, and runtime posture. Activates on phrases like "I want
  to build", "I have an idea", "help me plan this system", "workshop my
  idea", "start a new project", or when the current spec directory is empty
  or missing the foundational files (no L0_registry.yaml, no L2_modules/, no
  L1_conventions.yaml, no L5_operations.yaml). Drives an adaptive agent-led
  interview — the agent asks questions, the human answers, specs emerge.
  Produces discovery-notes.md, an L0 skeleton, one L2 module file per
  identified module, L1_conventions.yaml, and L5_operations.yaml. Does NOT
  produce atoms, types, errors, constants, policies, flows, or journeys —
  those belong to downstream skills.
---

# forge-discover

Conduct an agent-led interview that takes a human from a vague product idea to a complete Forge project foundation. You ask questions. The human answers. Specs emerge from the conversation and are written to disk incrementally. You are NOT a template-filler. You are a Socratic interviewer whose questions get more domain-specific as the conversation progresses — that adaptation is the single thing that separates a useful interview from a wasted one.

The full mental model is in `references/framework.md` (~750 lines). You do not need to read it end-to-end every run. Load it on demand when:
- You are unsure which question shape fits a novel situation (look up §4)
- You encounter a revision request mid-interview (look up §7)
- The human's answer doesn't clearly fit the current sub-phase (look up §5)
- You're about to present a critical option set and want the full guidance (look up §2a)

Otherwise, this file is self-sufficient for routine operation.

## Non-negotiables

1. **Batch within sub-phases; sequence across them.** Group questions that don't depend on each other into one turn — the human answers all at once rather than waiting through one-at-a-time prompts. Questions where answer B requires answer A stay sequential. Critical decisions (cloud, compute, persistence, event semantics, deployment strategy, auth posture) always get their own turn as an option-set — never batch a cascading choice with a routine one.
2. **Extractive, not generative.** Do NOT invent modules, capabilities, or features. Do NOT say "you probably need a User module" before the human has named user-related capabilities. Surface what the human already knows.
3. **Adapt every question to the domain model.** See `## The domain model (short-term memory)` below. Generic questions get generic answers; domain-grounded questions get spec-worthy ones.
4. **Confirm by restating before writing.** "So: when X happens, the system does Y. Right?" — then write to disk. Silence is not agreement.
5. **Critical decisions get option sets, not defaults.** For cascading choices (cloud, persistence, auth posture, event semantics, deployment strategy), present 2–4 options with tradeoffs instead of picking silently or proposing a single default. See `## Critical decisions`.
6. **Resist premature naming.** Work with descriptive placeholders ("the thing that does X," "whatever handles Y") until the boundary is tested. Only commit a 3-letter module ID after the seam has been interrogated.
7. **Scratchpad first, structured files second.** Everything captured goes into `discovery-notes.md` as it surfaces. Commit to structured YAML (L0/L1/L2/L5) only at sub-phase exits, once the shape is stable.

Full rationale: `references/framework.md` §2.

## Workflow

### Step 1 — Detect state (always first, always via the forge CLI)

Before asking anything, run:

```bash
forge list --spec-dir <spec-dir>
```

If `forge` is not on PATH, try `./.venv/bin/forge` or instruct the user to install. If the spec directory is unknown, ask the user for it, or default to `.forge/` when running inside a project repo (the canonical layout produced by `forge init`).

Parse the output to determine the entry sub-phase:

| Observed state | Entry sub-phase |
|---|---|
| Spec dir does not exist OR no `discovery-notes.md` AND no other spec files | **0** (product workshopping) |
| `discovery-notes.md` exists but thesis/user/pain/fence sections are empty or placeholder | **0** (resume where blank) |
| `discovery-notes.md` complete through fence; no `Capability inventory` section | **1** (system framing) |
| Capability inventory exists; no `L2_modules/*.yaml` files | **2** (module boundaries) |
| L2 module files exist; no `L0_registry.yaml` or missing skeleton sections | **3** (vocabulary baseline) |
| L0 skeleton done; no `L1_conventions.yaml` | **4** (project conventions) |
| L1 done; no `L5_operations.yaml` | **5** (platform & runtime posture) |
| All foundation files exist and parse | Skip to **Step 3 — Handover** |

If the `forge` CLI is unavailable, read the YAML files directly to determine the same state.

Announce the entry sub-phase to the user in one line: "Looks like you're at sub-phase 2 — I see 4 modules drafted but no L0 registry yet. Ready to continue?" Wait for confirmation before proceeding.

### Step 2 — Run the sub-phase

Each sub-phase below has: seed questions (generic templates you start from), adaptation rules (how to make them domain-specific from turn 2 onward), what to write, and when to exit.

**Every sub-phase shares these moves:**
- Ask one seed question, adapted to the domain model if any content is in it.
- When the human answers, update the domain model in `discovery-notes.md` FIRST (even before asking the next question).
- Use the updated model to pick the next question — either the next seed, a probing follow-up, or a consistency-check if something contradicts an earlier answer.
- At the end of each sub-phase, confirm exit criteria are met before moving on.

---

#### Sub-phase 0 — Product workshopping

**Purpose.** Take the human from a vague idea to a crystallized product thesis. This sub-phase writes NO structured YAML — only `discovery-notes.md`.

**Before any questions:** copy `assets/discovery-notes.template.md` to `<spec-dir>/discovery-notes.md` (or whatever root the human is working from). All sub-phase 0 output writes into this file.

**Seed questions — batch into three turns:**

**Turn 1 — orientation (none depend on each other):**
1. "In one or two sentences, what is this?"
2. "What's the pain? Tell me about a specific recent time it happened."
3. "Who specifically feels this pain? How often?"

**Turn 2 — solution (after you know what and who):**
4. "How do they solve it today?"
5. "What's meaningfully better about your solution? Be specific — 'faster' doesn't count."

**Turn 3 — shape and scope (independent of each other):**
6. "Is this a tool someone opens daily, a background service, a one-time workflow, or a platform?"
7. "Six months in, how do you know it worked?"
8. "What are you explicitly NOT building? Who is NOT a target user?"
9. "If you had two weeks, what's the smallest useful version?"

**Adaptation rules:**
- As soon as the human names a target user or role, STOP saying "a user" — use the exact role they named in every subsequent question.
- When the human names a pain or scenario, reference it back by its concrete details in later questions. Don't paraphrase it into generic terms; quote the specifics they gave you.
- When the human offers a comparison ("like X but for Y"), probe where the analogy breaks. Comparisons are shortcuts — always test their limits.
- If the human starts discussing architecture, tech choices, or implementation, push back: "Slow down — what problem are we solving for whom? Architecture comes later."

**Writes.** Update the corresponding section in `discovery-notes.md` after each answer. The `domain_model` block grows with every turn (actors, nouns, verbs, pains, constraints, vocab).

**Exit when all true:**
- Thesis paragraph reads as true, not aspirational.
- Target user is specific enough to imagine one person by name.
- Pain is backed by a concrete scenario, not an abstraction.
- A scope fence exists (any fence — "not yet decided" is acceptable).

**Transition line:** "OK — ready to move from 'what are we building' to 'how is it shaped'?"

---

#### Sub-phase 1 — System framing

**Purpose.** Ground the thesis in a concrete user session and extract the capability inventory. Still no structured YAML — only `discovery-notes.md`.

**Seed questions — batch all four (none depend on each other):**
1. "Walk me through one typical [target user] session start to finish."
2. "What kinds of changes will this system undergo every week? Every quarter? Every year?"
3. "If this system had one critical failure mode that must never happen, what would it be?"
4. "What's the hardest part of this system to get right?"

**Adaptation rules:**
- Use the target user from sub-phase 0 — never "a user."
- Use the human's verbs verbatim. Whatever terminology they use, you use — never translate their terms into synonyms you prefer.
- Use the pain from sub-phase 0 to probe where it happens in the session.
- Every verb the human uses in the walkthrough is a **capability candidate**. Extract it to the `Capability inventory` list.
- Every external system mentioned is an external integration. Add each to `External integrations observed` with service name, purpose, and auth method if known.

**Writes.** `Typical user session`, `Capability inventory`, `External integrations observed`, `Change axes`, `Critical failure modes` sections of `discovery-notes.md`.

**Exit when all true:**
- At least one complete user session is written as a narrative.
- Capability inventory has ≥3 items.
- External integrations are enumerated (even if empty).
- At least one critical failure mode named.

**Transition line:** "OK — we have N capabilities. Now let's find the seams between them."

---

#### Sub-phase 2 — Module boundaries

**Purpose.** Cut the capability inventory into modules along ownership and change-frequency seams. This is where the first structured YAML files get written: `L2_modules/<CODE>.yaml`.

**Boundary-finding questions (iterate over pairs of capabilities — not a broad "find the seams"):**
1. "Who owns the data that [capability A] touches?"
2. "Where could a change to [capability A] not need to touch [capability B]?"
3. "Could [A] and [B] plausibly run on different infra, different team, different tech stack?"
4. "What does [A] need from [B] — data, events, calls?"
5. "What changes on a different cadence from everything else?"

**Tech-stack questions (ask per-module, AFTER the boundary is confirmed):**
6. "Language and runtime for this module — project default, or does this module need its own?"
7. "Any frameworks or mandatory libraries pinned? (e.g., `nestjs@10`)"
8. "Cloud-managed services this module uses? (e.g., aws-rds, gcp-bigquery) — include purpose for each."
9. "Does this module's compute model match the project default, or override it?"

**Adaptation rules:**
- Iterate boundary questions over **named pairs** drawn from the capability inventory, not a generic "find seams" prompt.
- When a seam is confirmed, commit the module file immediately and assign a 3-letter ID matching `L0.naming_ledger.module_id`.
- When a capability's description contains a catch-all ("handles everything related to X"), push: "Is that one module or two? Where's the internal seam?"
- When two capabilities have circular dependencies, surface the cycle: "A needs B and B needs A — are these one module, or is there an event/interface between them?"
- If the project-wide cloud provider hasn't been established yet (usually set in sub-phase 5), record module tech_stack language/runtime/frameworks now but leave `managed_services` empty; add the module to the `Open questions` list to revisit after sub-phase 5.

**Anti-bloat: reuse-before-create (advisory, run every time before writing a module file).**

Before writing a new `L2_modules/<CODE>.yaml`, scan for potential overlap:

```bash
forge find <keywords-from-proposed-description> --kind module --spec-dir <dir>
```

If matches come back, present them to the human:

> *"Before committing `<proposed_id>`, I found modules with overlapping concerns:*
> *- `<existing_id>` — `<one-line>`*
> *Options: (a) merge into `<existing_id>`, (b) refine the new module's description to sharpen the distinction, (c) proceed — the boundary is genuinely distinct.*
> *Which?"*

Advisory only. Human may pick (c) without justification. The scan just makes overlap visible at the moment of creation.

**Tiered novelty challenge.**

- **Modules 1–3** (initial set): soft probe — *"What's one thing this module does that no other module does?"* Accept any substantive answer.
- **Module 4 onward**: hard probe — require the `description` field to contain a distinct-responsibility statement (something no prior module's description covers). If the human can't state it, probe for consolidation before proceeding.

Rationale: the first few modules define project concept axes; later modules have less excuse for vagueness because the shape of "what's distinct" is already established.

**Write per confirmed module** at `<spec-dir>/L2_modules/<CODE>.yaml`:

```yaml
module:
  id:          <3-letter CODE>
  name:        <human-readable>
  description: |
    <specific — say what this module owns and why the boundary exists>
  tech_stack:
    language:            <string>
    language_version:    <version>
    runtime:             <string>
    runtime_version:     <version>
    frameworks:          [<name@version>, ...]
    mandatory_libraries: [<name@version>, ...]
    compute:             <optional — only if overriding L5 default>
    managed_services:    []     # populated now if cloud is decided, or deferred to sub-phase 5
  owned_atoms:     []            # populated by forge-decompose
  owned_artifacts: []            # populated by forge-decompose
  persistence_schema:
    datastores:      []          # populated by forge-decompose / forge-atom
    storage_buckets: []
    caches:          []
    ownership:       exclusive
    shared_with:     []
  interface:
    entry_points: []             # populated by forge-decompose
  access_permissions:
    env_vars:         []
    filesystem:       []
    network:          []
    secrets:          []
    external_schemas: []
  dependency_whitelist:
    modules: [<other-CODEs>]
  policies: []
  changelog:
    - version:     "0.1.0"
      date:        <YYYY-MM-DD>
      change_type: added
      description: "Initial module from forge-discover."
```

Also update `discovery-notes.md` with a `Module map` ASCII diagram showing modules and dependency arrows.

**Exit when all true:**
- Every capability in the inventory is owned by exactly one module.
- Every inter-module dependency is declared in some module's `dependency_whitelist`.
- No module has a generic description like "does everything X-related."

**Transition line:** "Modules look clean. Now let's lock in the shared vocabulary — error categories, external services, naming patterns."

---

#### Sub-phase 3 — Vocabulary baseline (L0 skeleton)

**Purpose.** Populate `L0_registry.yaml` with the project-wide skeleton: `naming_ledger`, `error_categories`, `external_schemas`, `side_effect_markers`. Types, errors, and constants are left empty — they emerge from atoms in later skills.

**Seed questions — batch all four (independent confirmations):**
1. "Default atom ID regex is `^atm\.[a-z]{3}\.[a-z_]+$` — fit, or custom?" (iterate over the 10 naming_ledger classes)
2. "Standard error categories: VAL, SYS, BUS, SEC, NET, DAT, CFG, EXT — any domain-specific ones to add?"
3. "From sub-phase 1, I have these external integrations: [list]. Confirm, and give me the auth method for each (bearer / api_key / oauth2 / hmac / mtls / none)."
4. "Default side-effect markers (PURE, READS_DB, WRITES_DB, EMITS_EVENT, CALLS_EXTERNAL, READS_ARTIFACT, ...) — any custom markers your domain needs?"

Ask all four at once. Process answers individually — if any trigger follow-up (e.g., a new error category needs a name), handle that before moving to L1.

**Adaptation rules:**
- External integrations list comes from sub-phase 1 — don't re-ask, only confirm and fill in auth methods.
- If sub-phase 0 surfaced regulatory or audit-trail constraints → suggest an `AUDIT` or `COMPLIANCE` error category.
- If sub-phase 1 suggests ML/model components → ensure `READS_ARTIFACT` marker is in the set.
- If the domain has heavy async workflows → suggest `SCHED` error category.

**Write** `<spec-dir>/L0_registry.yaml` with four populated sections and three empty ones (`errors: {}`, `types: {}`, `constants: {}`).

**Exit when:** All four skeleton sections have human-confirmed content. File parses as valid YAML.

**Transition line:** "Good. Now project-wide defaults every atom will inherit."

---

#### Sub-phase 4 — Project conventions (L1)

**Purpose.** Set atom-level defaults every atom inherits: failure policy, observability, security posture, verification floors, audit triggers, idempotency, allowed overrides.

**Approach.** Propose a FULL draft `L1_conventions.yaml` based on the domain model, then review it section-by-section. Only interrogate deeply where the human wants to deviate.

**Critical decisions in this phase** (present as option sets if not already signaled):
- **Security posture** — required vs optional vs none auth; which auth methods are acceptable. Options: (1) bearer + api_key (typical for machine-to-machine / programmatic APIs), (2) oauth2 + session (typical when users hold accounts), (3) mtls + hmac (typical for internal service-to-service). Present options.
- **Role model** — pick from common patterns or bespoke. Options: (1) user/admin (flat), (2) user/admin/service/auditor (typical with audit), (3) RBAC with custom roles.

**Routine decisions in this phase** (propose default, ask to deviate):
- Default log level, template strings
- Per-category failure defaults (retries, backoff)
- Verification floors (min assertions/edges/examples)
- Idempotency requirements by marker
- Overrides: which L1 fields may atoms override; require justification?

**Adaptation rules:**
- If sub-phase 0 pain involves reliability → stricter failure defaults (more retries on NET, halt_and_alert on DAT, higher verification floors).
- If sub-phase 0 shape is "consumer-facing" → INFO default log level with verbose templates.
- If sub-phase 0 surfaced regulatory constraints → audit triggers on all WRITE markers + CALLS_EXTERNAL; require ownership checks.
- Only use error categories that exist in L0 — don't propose defaults for categories that weren't declared in sub-phase 3.

**Write** `<spec-dir>/L1_conventions.yaml` with all seven sections.

**Exit when:** Human has accepted or deviated on each of the seven L1 sections. File parses.

**Transition line:** "Last piece — platform-level posture."

---

#### Sub-phase 5 — Platform & runtime posture (L5)

**Purpose.** Set deployment platform, rollout strategy, rate limits, and event semantics. This sub-phase has the **highest concentration of critical decisions** — several must be presented as option sets, not defaults.

**Critical decisions (present as option sets if not already signaled):**

- **Cloud provider** — if not mentioned in sub-phases 0–2, use the option-set template in `## Critical decisions` below. Record in `deployment.platform.cloud` (free-form string).
- **Default compute model** — given the chosen cloud, present 3–4 options (serverless / managed containers / kubernetes / VMs) with tradeoffs.
- **Primary persistence model** — relational / document / key-value / mixed; present as options.
- **Deployment strategy** — rolling / canary / blue-green / recreate; present options unless already clear.
- **Event delivery semantics** — at-most-once / at-least-once / exactly-once; present options (especially exactly-once: usually only justified when duplicate delivery has serious consequences — money movement, inventory changes, safety-critical actions).

**Routine decisions — batch together (propose defaults for all, human adjusts):**
- Environments list (default `[dev, staging, prod]`)
- Rate limits per auth method
- Event ordering (fifo_per_key vs unordered) and ordering key field
- Canary weights (if canary chosen)
- Rollback automatic triggers
- Observability stack (default `prometheus-alertmanager-grafana`; ask only if not PAG)
- Observability defaults: latency_p99_ms (propose 500ms), error_budget_percent (propose 1.0), trace_sample_rate (propose 0.1)
- Per-module SLA targets: for each module, propose a latency budget derived from its description and the overall system shape (e.g., payment-critical modules get 200ms; background workers get 1000ms). Present as a table: "Here are proposed per-module SLAs — adjust any."

Present all routine decisions in one turn as a proposed block. Example:

> *"Routine platform decisions — proposed defaults (adjust any):*
> *- Environments: [dev, staging, prod]*
> *- Rate limits: 60 rpm default, 600 bearer, 1200 api_key, per_actor scope*
> *- Event ordering: fifo_per_key on customer_id*
> *- Canary weights: [5, 25, 50, 100]*
> *- Rollback: error_rate > 5% for 5min, p99 > 2x baseline for 10min*
> *- Observability: prometheus-alertmanager-grafana*
> *- SLA defaults: p99 500ms, error budget 1%, trace rate 10%*
> *- Per-module SLAs: PAY 200ms / 0.5%, USR 300ms / 1%, [others 500ms / 1%]*
> *Confirm or adjust each."*

**Adaptation rules:**
- If sub-phase 0 pain involved data consistency or transactional integrity → lean toward at-least-once or exactly-once; flag this bias when presenting options.
- If sub-phase 0 shape is "background service" → rate limiting less critical; ordering more important.
- If sub-phase 0 surfaced regulatory or compliance constraints → restrict cloud options to those that meet them (signed agreements, relevant certifications); note each constraint in the "best for" line of each option.
- If external integrations in sub-phase 3 have strict rate limits → propose conservative outbound rate limits.
- **After cloud and compute are decided**, revisit every `L2_modules/*.yaml` drafted in sub-phase 2 without `managed_services`. Ask: "For module X, which managed services does it use now that we're on [cloud]?" Update those module files.

**Write** `<spec-dir>/L5_operations.yaml` with all four sections. Include `deployment.platform` only if cloud/compute were established. Include `observability` with at minimum `stack` and `defaults`; populate per-module blocks for any module whose SLA was discussed. Leave `metrics`, `alerts`, and `atom_overrides` empty at discover — those are filled progressively during `forge-atom`.

**Exit when:** File parses. All L2 modules have populated `managed_services` (no deferred entries in `open_questions`).

### Step 3 — Handover

When all foundation files exist and parse, wrap the interview:

1. **Summarize** what was produced: file inventory, module count, key decisions (cloud, persistence, delivery semantics).
2. **Recommend** which module to decompose first. Heuristic: the module covering the capability the human flagged as "hardest to get right" in sub-phase 1.
3. **Hand off** with: "Next step is `forge-decompose <CODE>` to break [MODULE] into atoms. Ready to start there, or do you want to revise anything first?"

Full termination protocol: `references/framework.md` §8.

## The domain model (short-term memory)

This is the running state the agent maintains in `discovery-notes.md`'s `Domain model` section. Every turn, update it FIRST, then use it to adapt the next question.

```yaml
domain_model:
  actors:         # named roles — specific, not generic ("a user" is not specific enough)
  nouns:          # objects of concern in the human's vocabulary
  verbs:          # operations in the human's vocabulary
  pains:          # concrete frustrations with scenarios
  constraints:    # hard limits (regulatory, platform, temporal)
  vocab:          # domain terms defined in the human's own words
  comparisons:    # analogies the human accepted or rejected
  open_questions: # things to revisit
```

**Adaptation primer:** at turn 1, all questions are generic templates. At turn 2+, every question you ask should substitute at least one element from the domain model into the template. By turn 6, your questions should be answerable only by someone familiar with this specific domain.

Worked example of question evolution across 6 turns: `references/framework.md` §3 ("How questions evolve").

## Critical decisions: present options, don't default

**When to present options instead of a default:** any decision that cascades through the spec, encodes domain-specific assumptions, or is hard to reverse. Specifically: cloud provider, compute model, primary persistence, event semantics, default transaction boundary, security posture, auth methods, deployment strategy, multi-tenancy model.

**Option-set template:**

```
You haven't mentioned [decision]. This will cascade through the spec.
Your options:

1. **[Option A]** — [one-line benefit]. [one-line tradeoff]. Best for [context].
2. **[Option B]** — [one-line benefit]. [one-line tradeoff]. Best for [context].
3. **[Option C]** — [one-line benefit]. [one-line tradeoff]. Best for [context].

Which fits your context? Happy to go deeper on any of these.
```

**Rule of thumb:** presenting options costs one turn; a silently-wrong default costs hours of rework. When in doubt, present options.

Full decision-criticality framework (including heuristic for "is this critical?"): `references/framework.md` §2a.

## Gotchas

- **The forge CLI's `list` command exits 0 on missing spec dirs — don't assume exit code means existence.** Parse the output for `# Total entries:` or similar. Missing spec dir or empty dir should be treated as sub-phase 0 entry.
- **The skill writes files to disk between turns.** If the session is interrupted, resuming works because state lives on disk. Do not try to keep the domain model only in conversation memory.
- **Do NOT produce atoms, types, errors, constants, policies, flows, or journeys during discover.** These come from downstream skills. Producing them here creates cruft because you're guessing at structure the atoms haven't yet forced.
- **Module files written in sub-phase 2 may have empty `managed_services` if the cloud isn't yet decided.** This is expected — sub-phase 5 fills them in. Track deferred modules in `discovery-notes.md`'s `Open questions`.
- **The error `ScannerError: mapping values are not allowed here` when loading a spec file usually means an unquoted flow-style string in a `logic` or `render_contract` entry.** Wrap the offending list item in single quotes.
- **Do not interpret silence as agreement, especially on critical decisions.** If the human doesn't respond to a proposal, ask explicitly: "Want to go with that, or something different?"
- **Always restate before writing.** If the human says "yes, sounds good" to a complex proposal, restate it in your own words and get a second confirmation before committing to YAML.

## forge CLI commands used by this skill

| Command | Purpose |
|---|---|
| `forge list --spec-dir <dir>` | At entry: determine which sub-phase to resume. Count modules, check for foundation files. |
| `forge list --kind <kind> --spec-dir <dir>` | Enumerate a specific entity type (e.g., `--kind module` to see what modules exist). |
| `forge list --kind module --ids-only --spec-dir <dir>` | Pipe-ready module ID list (e.g., to iterate over modules at sub-phase 5 for managed_services fill-in). |
| `forge inspect <id> --spec-dir <dir>` | Lightweight metadata probe for a specific entity. Useful when revising. |

**Not typically needed by forge-discover** (but documented for completeness): `forge context <id>` — heavyweight dependency walk, used by `forge-decompose` and `forge-atom`, not by discover.

## References

- `references/framework.md` — full mental model. Sections: §2 operating principles rationale, §2a decision criticality (load before presenting critical options), §3 adaptive questioning worked example, §4 question shape taxonomy, §5 per-sub-phase deep guidance, §7 revision protocol, §8 termination, §10 artifact schemas.
- `assets/discovery-notes.template.md` — scratchpad template. Copy to project root at sub-phase 0 start.
