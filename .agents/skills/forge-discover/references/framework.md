# forge-discover — Framework

This document describes the **mental model** for `forge-discover`: the stages, the question shapes, the adaptation rules, and the artifacts produced. It is **not** the SKILL.md; it is the source of truth from which any skill artifact — Claude Code, agentskills.io-format, Cursor, or a human-facilitated workshop — is authored.

The three audiences for this doc:

- An LLM or agent that executes the process
- An engineer writing the `SKILL.md` from this framework
- A human facilitator running the process without an AI

---

## Contents

| § | Section |
|---|---|
| §1 | What `forge-discover` is |
| §2 | Operating principles |
| §2a | Decision criticality — when to default vs. present options |
| §3 | Adaptive questioning — the core concept |
| §4 | Question shape taxonomy |
| §5 | The six sub-phases (0–5) |
| §6 | State detection protocol |
| §7 | Revision protocol |
| §8 | Termination |
| §9 | What `forge-discover` does NOT produce |
| §10 | Artifact schemas |

---

## 1. What `forge-discover` is

**Purpose.** Take a human from a vague idea to a complete foundation for the Forge spec system: a product thesis, a module map, and the project-wide vocabulary/conventions/posture files that every atom will later reference.

**Inversion of the default AI-dev loop.** Instead of *human prompts agent → agent implements*, `forge-discover` runs *agent interviews human → human explains → structured spec emerges*. The premise is that people explain systems well under questioning but poorly when cold-prompted.

**Specific outputs at exit:**

| Artifact | Contains | Purpose |
|---|---|---|
| `supporting-docs/discovery-notes.md` | Thesis, user, pain, scope fence, MVP cut, running **domain model** | Scratchpad + the human-facing record of what was decided and why |
| `L2_modules/<CODE>.yaml` (one per module) | `id`, `description`, `dependency_whitelist`, empty `owned_atoms` | Module boundaries; consumed by `forge-decompose` |
| `L0_registry.yaml` skeleton | `naming_ledger`, `error_categories`, `external_schemas`, `side_effect_markers` only | Project vocabulary root; populated further by `forge-atom` |
| `L1_conventions.yaml` | All seven sections | Atom-level defaults every atom inherits |
| `L5_operations.yaml` | All three sections | Runtime posture |

Nothing atom-specific is produced. No `types`, no `errors`, no `constants`, no atoms, no policies, no flows, no journeys. Those emerge from downstream skills.

---

## 2. Operating principles (non-negotiable across all sub-phases)

1. **Batch within sub-phases; sequence across them.** Group questions that don't depend on each other into one turn — the human answers all at once rather than waiting through one-at-a-time prompts. Questions where answer B requires answer A stay sequential. Critical decisions (cloud, compute, persistence, event semantics, deployment strategy, auth posture) always get their own single turn as an option-set — never batch a cascading choice with a routine one.
2. **Concrete before abstract.** Always ask for an example before asking for a rule. "Walk me through one specific instance" before "how does this work in general."
3. **Extractive, not generative.** The agent never invents structure. It surfaces what the human already knows. If the agent is tempted to say "you need a User module and an Order module," stop — the human hasn't said that yet.
4. **Confirm by restating before writing.** "So: when X happens, the system does Y. Right?" Silence is not agreement.
5. **Scratchpad first, structured files second.** Everything goes into `supporting-docs/discovery-notes.md` as it surfaces. Commit to structured YAML only at sub-phase exits, once the shape is stable.
6. **Ground new questions in prior answers.** See Section 3. This is the most important principle specific to this skill.
7. **Resist premature naming.** Work with descriptive placeholders ("the thing that does X," "whatever handles Y") until the boundary is stable. Naming before that freezes bad seams.
8. **Offer defaults explicitly, never silently.** For routine decisions with a sensible default, propose it and ask whether to deviate. Never interpret silence as acceptance.
9. **Revision is first-class.** At any point the human can say "let's revise X." The skill walks back, never starts over — the domain model preserves context.
10. **Critical decisions get option sets, not defaults.** When a decision cascades through the spec, encodes fundamental domain assumptions, or is hard to reverse, and the human has not signaled a preference, the agent **presents 2–4 options with tradeoffs** and lets the human choose. This is stronger than principle #8: even "here's a default" is too opinionated when the stakes are high. See Section 2a.

---

## 2a. Decision criticality — when to default vs. present options

Criticality governs how the agent surfaces a decision. Get this distinction wrong and the interview either wastes turns (presenting options for log levels) or forecloses the future (silently picking AWS when the human hasn't said).

### Critical decisions

Cascading, hard-to-reverse, domain-shaping. If the human has not signaled a preference, the agent **must** present an option set with tradeoffs:

| Decision | Why it's critical |
|---|---|
| Cloud provider (AWS / Azure / GCP / multi-cloud / on-prem) | Shapes every module's services, secrets, policies, observability |
| Default compute model (Lambda / ECS / Cloud Run / Kubernetes / VMs) | Affects atom implementation patterns, cold-start assumptions, scaling |
| Primary data persistence (relational / document / key-value / graph) | Affects `types` shapes, transaction boundaries, invariants |
| Event delivery semantics (at-most-once / at-least-once / exactly-once) | Affects idempotency requirements across all `EMITS_EVENT` atoms |
| Default transaction boundary (saga / acid / none) | Affects flow design and compensation requirements |
| Security posture (auth required / optional; role model) | Changes every entry point's threat surface |
| Authentication methods (bearer / oauth2 / session / mtls) | Shapes every external interface |
| Deployment strategy (rolling / canary / blue-green / recreate) | Affects rollout risk and rollback design |
| Multi-tenancy model (shared DB / DB-per-tenant / account-per-tenant) | Shapes persistence_schema across every module |

### Routine decisions

Standard sensible defaults exist; deviation is cheap. Propose a default and ask whether to change:

- Default log level
- Standard error category taxonomy (VAL / SYS / BUS / ...)
- `naming_ledger` regex patterns
- Verification floors (min assertions / edge cases / examples)
- Default retry counts and backoff within an already-chosen failure policy
- Audit trigger markers

### Option-set presentation template

When presenting a critical option set, use this structure:

```
You haven't mentioned [decision]. This will cascade through the spec.
Your options:

1. **[Option A]** — [one-line benefit]. [one-line tradeoff]. Best for [context].
2. **[Option B]** — [one-line benefit]. [one-line tradeoff]. Best for [context].
3. **[Option C]** — [one-line benefit]. [one-line tradeoff]. Best for [context].

Which fits your context? Happy to go deeper on any of these.
```

**Example — cloud provider:**

> You haven't mentioned a cloud provider. This shapes everything downstream — services, secrets, policies. Your options:
>
> 1. **AWS** — widest service catalog, largest hiring pool. Heavier ops surface. Best if you expect broad third-party integration or want commodity expertise.
> 2. **Azure** — strong enterprise / compliance story, tight Microsoft ecosystem (M365, Entra ID). Best if selling into enterprise or leveraging existing MS stack.
> 3. **GCP** — strong data / ML primitives (BigQuery, Vertex AI), simpler ops surface. Best if analytics or ML is central.
> 4. **Multi-cloud or on-prem** — more complex; pick only if regulation or a specific customer mandate forces it.
>
> Which fits? I can go deeper on any.

### Heuristic: is this critical?

If any are true, treat as critical:

- Changing it later requires touching multiple module files
- It encodes a domain-specific assumption (regulatory, scale, reliability, tenancy)
- It affects what L0 entries get produced downstream (types, errors, external_schemas)
- The wrong choice has compounding cost across many atoms

If in doubt, treat as critical. Presenting options costs one turn; a silently-chosen wrong default costs hours of rework.

### When the human has already signaled

If sub-phase 0 or 1 surfaced a preference (e.g., the human named a specific cloud they're already on, or a regulatory constraint that forces a particular platform), record it in the domain model and **skip the option set** — just confirm in passing. The agent presents options only when there is genuine ambiguity.

---

## 3. Adaptive questioning — the core concept

**A question has two layers: *shape* and *content*.**

- **Shape** = what the agent is trying to learn (e.g., "find a boundary seam," "surface a hidden constraint," "pin down a term").
- **Content** = the actual words the agent speaks. Early in the interview, content comes from generic templates. As the interview progresses, content comes from a growing **domain model** — the human's own vocabulary, their named actors, their stated pains, their concrete examples.

This is the single feature that separates a useful interview from a useless template. Generic questions get generic answers. Specific questions get spec-worthy answers.

### The domain model the agent maintains

Every turn, the agent updates a running model in `supporting-docs/discovery-notes.md`. The example below uses a single illustrative domain to show what a populated model looks like; the structure applies to any project area.

```yaml
domain_model:
  actors:        # who uses or is affected by the system, with names and roles
    - "solo accountant at a 1-3 person firm"
    - "partner at a 10-50 person firm"
    - "client (end customer of the firm)"
  nouns:         # the objects of concern (entities, documents, artifacts)
    - invoice
    - journal_entry
    - ledger
    - trial_balance
  verbs:         # the operations the system performs on nouns
    - reconcile
    - post
    - approve
    - close
    - audit
  pains:         # concrete frustrations with scenarios, not abstractions
    - "reconciling 200 transactions takes a full day of manual matching"
    - "the $0.50 discrepancy that nobody can track down"
  constraints:   # hard limits — regulatory, platform, temporal
    - "must produce IRS-compliant audit trail"
    - "cannot store PAN / SSN in plaintext"
    - "month-end close must complete within 5 business days"
  vocab:         # domain-specific terms the human introduced, in their words
    close: "the month-end reconciliation and lock process"
    matching: "pairing bank transactions to ledger entries"
  comparisons:   # analogies the human made or accepted
    - "like QuickBooks but for firms managing 20+ clients"
    - "not like Xero — no POS integration needed"
  open_questions: # things the human was unsure about, to revisit
    - "unclear if multi-currency is in scope"
```

This is short-term memory across the interview. Every new question draws from it.

### How questions evolve — a worked example

A simple progression showing how the same question **shape** produces different **content** as the domain model grows. The example uses one illustrative domain; the adaptation mechanism applies regardless of what the human is building.

| Turn | Shape | Generic template | Content actually spoken |
|---|---|---|---|
| 1 | Grounding | "Who uses this system?" | "Who uses this system?" |
| 2 | Probing | Based on answer "accountants at small firms" → add to `actors` | "Got it. When you say 'small firm' — how many people? Solo, 3-person, 20-person?" |
| 3 | Grounding | "Walk me through a typical session." | "Walk me through a typical Monday morning for a solo accountant at a 3-person firm." |
| 4 | Probing | Session mentioned "reconcile" → add to `verbs` | "You said they spend an hour reconciling Friday's transactions. What goes wrong when reconciliation doesn't produce a clean match?" |
| 5 | Constraint-surfacing | Pain surfaced → add to `pains` | "You mentioned the $0.50 discrepancy that takes half a day to find. That's a pain signal — is speed of resolution a core success metric, or is finding the cause the point?" |
| 6 | Boundary-finding (sub-phase 2) | "Where could X change without touching Y?" | "You described reconciliation and ledger-posting as separate activities that happen in that order. Could you imagine changing the reconciliation UI without touching how posting works? That's a seam candidate." |

By turn 6, the agent is asking questions only answerable by someone who has just described this specific domain. That's the adaptive principle working.

### Why this matters for spec quality

Specs produced by a generic interview look like marketing copy. Specs produced by an adaptive interview look like truth. Example — the output of a sub-phase 0 exit for the same idea, under both regimes:

**Generic interview (bad):**
> A financial tool that helps accountants streamline their workflow.

**Adaptive interview (what forge-discover produces):**
> A workbench for solo-to-small-firm accountants that cuts month-end close from 5 days to 2 by automating bank-to-ledger reconciliation for firms managing 20+ clients. Primary pain addressed: the manual 200-transaction matching that currently takes a full day and the follow-on $0.50 discrepancies that take half a day to trace.

Both are one paragraph. Only the second is a thesis you can spec against.

---

## 4. Question shape taxonomy

Every question in `forge-discover` is one of these shapes. Sub-phases draw from this menu in different proportions.

| Shape | Purpose | Generic form |
|---|---|---|
| **Grounding** | Anchor abstract discussion in a concrete case | "Walk me through one typical [X] step by step." |
| **Probing** | Dig into the specifics of something just mentioned | "When [X] happens, what exactly [Y]?" |
| **Boundary-finding** | Identify change/ownership seams | "Where could [X] change without affecting [Y]?" |
| **Consistency-checking** | Surface contradictions | "Earlier you said [A]; now [B] — which wins?" |
| **Constraint-surfacing** | Find hard limits the human hasn't stated | "What must never happen?" |
| **Scope-fencing** | Bound what's in vs. out | "What are you explicitly NOT building?" |
| **Vocabulary-anchoring** | Pin down a term the human has used loosely | "When you say '[X]', do you mean [A] or [B]?" |
| **Analogical** | Compare to known systems to triangulate shape | "Is this more like [X] or [Y]?" |
| **Defaulting** | Offer a default and probe for deviation | "Most projects do [X] — does that fit, or want different?" |
| **Prioritization** | Force a choice between competing goods | "If you had to pick one, [A] or [B]?" |
| **Hypothetical** | Test the edge of the current spec | "What if [unusual case]?" |

Most sub-phases lean on 3–5 of these predominantly.

---

## 5. The six sub-phases

Each sub-phase has:
- **Purpose** — what it's trying to achieve
- **Entry trigger** — state-detection rule for starting here
- **Primary shapes** — which question shapes dominate
- **Seed questions** — the generic templates (content before adaptation)
- **Adaptation rules** — how content specializes as the domain model grows
- **Techniques** — skill-specific moves beyond just questioning
- **Outputs** — what gets written to disk
- **Exit condition** — how to know the sub-phase is done

### Sub-phase 0 — Product workshopping

**Purpose.** The human arrives with a vague idea or frustration. Leave with a crystallized product thesis.

**Entry trigger.** No `supporting-docs/discovery-notes.md`, no spec dir. Or the human says "I have an idea I'm working through."

**Primary shapes.** Grounding, probing, scope-fencing, analogical, prioritization.

**Seed questions (generic templates):**
- "In one or two sentences, what is this?"
- "What's the pain — tell me about a specific recent time this happened to you or to a target user."
- "Who specifically feels this pain? How often?"
- "How do they solve it today?"
- "What's meaningfully better about your solution vs. what exists now? 'Faster' doesn't count — be specific."
- "Is this a tool someone opens daily, a background service, a one-time workflow, or a platform?"
- "Six months in, how do you know it worked?"
- "What are you explicitly NOT building? Who is NOT a target user?"
- "If you had two weeks, what's the smallest useful version?"

**Adaptation rules:**
- Once the human names a target user or role → subsequent questions use that exact role. Not "a user" — the specific role they named.
- Once the human names a pain → subsequent questions ground in it. Reference the concrete details they gave (numbers, durations, scenarios) rather than paraphrasing.
- Once the human offers a comparison ("like X but for Y") → test where the analogy breaks. Comparisons are shortcuts; always probe their limits.

**Techniques:**
- **Challenge scope.** "What if we didn't build [X]? Would the product still work?"
- **Force a choice.** When the human names two distinct user groups or use cases, make them pick one as primary; the other becomes secondary or later.
- **Ask about competition.** "Tools already do this — why does yours exist?" (Surfaces the real differentiator.)
- **Push back on implementation talk.** If the human starts discussing architecture, say "slow down — what problem are we solving for whom?" Do not let the conversation jump to system design until the product is clear.

**Outputs.** Partial `supporting-docs/discovery-notes.md`:
```markdown
## Product thesis
<one paragraph — the distilled "what" and "for whom">

## Target user
<specific — imagine one person by name>

## Pain / job-to-be-done
<concrete, with a scenario>

## Delta vs. status quo
<what's meaningfully better>

## Shape
<tool | service | workflow | platform — one line>

## Success signal
<what "this worked" looks like at month 6>

## Scope fence
<what's explicitly not in scope; who is not a target user>

## MVP cut
<the 2-week version>

## Domain model
<the running yaml from section 3 — populated so far>
```

**Exit condition.**
- The thesis paragraph reads as true, not aspirational.
- The target user is specific enough to imagine one person by name.
- The pain is backed by a concrete scenario, not an abstraction.
- A scope fence exists (any fence — "not yet decided" is OK).

**Transition to sub-phase 1.** "OK — ready to move from 'what are we building' to 'how is it shaped'?"

---

### Sub-phase 1 — System framing

**Purpose.** Ground the thesis in a concrete user session and extract the capability inventory.

**Entry trigger.** Thesis / user / pain / fence filled in `supporting-docs/discovery-notes.md`.

**Primary shapes.** Grounding, probing, constraint-surfacing. Boundary-finding begins softly here.

**Seed questions:**
- "Walk me through one typical user session start to finish."
- "What kinds of changes will this system undergo every week? Every quarter? Every year?"
- "If this system had one critical failure mode that must never happen, what would it be?"
- "What's the hardest part of this system to get right?"

**Adaptation rules:**
- Use the target user named in sub-phase 0 — not "a user."
- Use the verbs the human uses verbatim. Whatever terminology they chose, the agent uses — never translate into synonyms.
- Use the pain from sub-phase 0 to probe where it happens in the session: reference the concrete scenario they gave (numbers, durations, specifics), not a paraphrase.

**Techniques:**
- **Extract capabilities as the session narrates.** Every verb is a capability candidate.
- **Extract entity candidates alongside capabilities.** Every noun the human names that represents a thing the system stores, transforms, or acts on is an entity candidate. Record: name, likely owning module, key identifying fields if named, which capabilities operate on it. When the human describes relationships ("an Order belongs to a Customer"), record them — these become persistence schema hints and L0 type composition signals.
- **Flag external dependencies as they arise.** When the human mentions a third-party system, probe: "That's an external integration — which provider? What's the auth method?" Add to the domain model.
- **Name-only, don't commit.** Work with descriptive capability labels (what they do) before committing to 3-letter module codes.

**Outputs.** Updates to `supporting-docs/discovery-notes.md`:
```markdown
## Typical user session
<narrative, written in the user's vocabulary>

## Capability inventory
- <capability 1 — placeholder name>
- <capability 2>
- ...

## Entity candidates
- <entity name> — owned by: <likely module> — key fields: <if named> — operated on by: <capabilities>
- ...

## External integrations observed
- <service — purpose — auth method if known>

## Change axes
- Weekly: <what changes often>
- Yearly: <what's stable>

## Critical failure modes
- <failure — consequence>

## Domain model
<growing — more verbs, more nouns, more pains>
```

**Exit condition.**
- At least one complete user session is written with verbs the agent can point at later.
- Capability inventory has ≥3 items.
- Entity candidates list populated from nouns in the walkthrough.
- External integrations are enumerated.
- At least one critical failure mode named.

**Transition to sub-phase 2.** "OK — we have N capabilities. Now let's find the seams between them."

---

### Sub-phase 2 — Module boundaries

**Purpose.** Cut the capability inventory along ownership and change seams. Produce draft L2 module files.

**Entry trigger.** Capability inventory exists.

**Primary shapes.** Boundary-finding (dominant), consistency-checking, vocabulary-anchoring, prioritization.

**Seed questions (boundary layer):**
- "For each capability, who owns the data it touches?"
- "Where would a change to [X] not need to touch [Y]?"
- "Can [X] and [Y] plausibly run on different infra, different team, different tech stack?"
- "What does [X] need from [Y] — data, events, calls?"
- "What changes on a different cadence from everything else?"

**Seed questions (tech_stack layer, per module, once boundary is confirmed):**
- "Language and runtime for this module — is it the project default, or does this module need its own?"
- "Any frameworks or mandatory libraries pinned for this module? (e.g., `nestjs@10`, `prisma@5`)"
- "Does this module use cloud-managed services? (e.g., RDS, DynamoDB, S3, Pub/Sub) — list each with its purpose."
- "Does this module's compute model match the project default, or does it differ? (e.g., project is Lambda but this module runs on ECS for long-lived connections)"

**Adaptation rules:**
- Iterate boundary questions over **ordered pairs** of capabilities the human named — not a broad "find the seams." Use specific pairs drawn from the capability inventory.
- When a seam is confirmed, commit it to a draft module file and name it (3-letter code following `naming_ledger.module_id`). Naming is now OK because the seam has been tested.
- When a capability's description contains a catch-all ("handles everything X-related"), push: "Is that one module or two? Where's the internal seam?"
- When two capabilities have circular dependencies, surface the cycle: "A needs B and B needs A — are these one module, or is there an event/interface between them?"
- **Tech stack is usually routine, occasionally critical.** If the project-wide cloud provider is already decided, language/runtime defaults from sub-phase 0/1 are routine. BUT if a module needs a managed service unavailable on the chosen cloud, flag this — it's critical. Similarly, if a module needs a compute model that contradicts the project default, probe why before accepting.
- **External managed services populate the module's `access_permissions.external_schemas` list,** which in turn forces matching `L0.external_schemas` entries in sub-phase 3. Record them now; the agent will need to confirm auth methods later.

**Techniques:**
- **Ownership is the primary test.** If two capabilities both write to the same datastore, they are one module unless there's a very clear reason.
- **Change-frequency test.** If two capabilities change on different cadences, they are candidates for separation.
- **Team test.** "Could a different team own [X] without needing to talk to [Y]'s team daily?"
- **Draft on the fly.** As each module's boundary firms up, write `L2_modules/<CODE>.yaml` with `id`, `description`, `tech_stack`, `dependency_whitelist`, and any already-identified `managed_services` under `tech_stack`. Leave `owned_atoms` empty — `forge-decompose` will populate it.
- **Defer if the cloud isn't decided.** If the project-wide cloud provider hasn't been established (either via human signal or sub-phase 5 hasn't happened yet), record module tech_stack language/runtime/frameworks now but leave `managed_services` empty and flag it in `open_questions`. The module will revisit this after sub-phase 5.

**Anti-bloat — reuse-before-create (advisory):**

Before committing a draft module file, run a scan for potential overlap with already-drafted modules:

```bash
forge find <keywords-from-proposed-module-description> --kind module --spec-dir <dir>
```

If the scan surfaces any existing module whose name or description overlaps meaningfully with the proposed one, present the matches:

> *"Before committing `<proposed_id>` (`<one-line description>`), I found existing modules with overlapping concerns:*
> *- `<existing_id>` — `<one-line>` — overlap on `<signal>`*
> *Options: (a) merge the proposed capabilities into `<existing_id>`, (b) refine the proposed module's description to make the distinction sharp, (c) proceed — the boundary is genuinely distinct.*
> *Which fits?"*

Enforcement is **advisory**: the human may choose (c) without a justification requirement. The scan just makes overlap visible at the moment of creation.

**Tiered novelty challenge:**

- **Modules 1–3** (the initial set, where the vocabulary is still forming): soft probe — ask *"what's one thing this module does that no other does?"* and accept any substantive answer. Purpose: surface duplicates, not block progress.
- **Module 4 onward**: hard probe — require the module's `description` field to contain a distinct-responsibility statement (something specific to this module that none of the already-drafted modules' descriptions cover). If the human can't state it, probe for consolidation with an existing module before proceeding.

The rationale: the first few modules define the project's concept axes; later modules have less excuse for vagueness because the shape of "what's distinct here" is already established.

**Outputs.**
- Draft `L2_modules/*.yaml` files (one per module).
- Updates to `supporting-docs/discovery-notes.md` with a module map (ASCII diagram of modules and dependency arrows).

**Exit condition.**
- Every capability is owned by exactly one module.
- Every inter-module dependency is declared.
- No module has "does everything" in its description — descriptions are specific.

**Transition to sub-phase 3.** "Modules look clean. Now let's lock in the shared vocabulary — error categories, the external services you named, naming patterns."

---

### Sub-phase 3 — Vocabulary baseline (L0 skeleton)

**Purpose.** Establish the project-wide vocabulary skeleton that every atom will later reference. The four skeleton sections are `naming_ledger`, `error_categories`, `external_schemas`, `side_effect_markers`. In addition, write preliminary entity type stubs for qualifying entities — these act as type anchors before atom elicitation and are the primary mechanism for preventing cross-atom contract drift.

**Entry trigger.** L2 modules drafted.

**Primary shapes.** Defaulting (dominant), vocabulary-anchoring, probing.

**Seed questions:**
- "Default naming regex for atoms is `atm.<3-letter-module>.<snake>`. Want different conventions for any entity class?" (iterate through the 10 classes)
- "Standard error categories: VAL, SYS, BUS, SEC, NET, DAT, CFG, EXT. Any domain-specific ones to add?"
- "I have [external integrations listed in sub-phase 1] on file. Confirm each, and give me the auth method."
- "Default side-effect markers: PURE, READS_DB, WRITES_DB, EMITS_EVENT, CALLS_EXTERNAL, READS_ARTIFACT, etc. Any custom markers this project needs?"

**Adaptation rules:**
- External integrations from sub-phase 1 become the starting list here. Don't re-ask — only confirm and add auth methods.
- If sub-phase 0 surfaced regulatory constraints (audit trails, compliance regimes) → suggest an `AUDIT` or `COMPLIANCE` error category.
- If sub-phase 1 suggested ML or probabilistic components → ensure `READS_ARTIFACT` marker is present.
- If the project has heavy async workflows (batch jobs, schedules) → suggest a `SCHED` error category.

**Techniques:**
- **Default-heavy.** The agent proposes a full skeleton `L0_registry.yaml` based on the example fixture plus what the domain model implies. Human edits by exception.
- **Entity-to-framework mapping (5th step after the four skeleton questions).** Take the `Entity candidates` list from sub-phase 1 and for each qualifying entity: (a) show the human how it maps into the framework — which atoms will use it as input/output, which module owns it in `persistence_schema`; (b) write a preliminary L0 type stub with empty `fields: []`. forge-atom will fill in the fields as it elicits each atom.

  Write stubs only for entities that satisfy at least one of:
  - Referenced by ≥2 different capability verbs (crosses multiple operations)
  - Referenced by atoms in more than one module (cross-module shared type)

  Single-module single-operation entities defer to forge-atom — writing them now is premature commitment.

  Stub format — type IDs follow the `reg.<mod>.<TypeName>` naming convention (module codes are already committed by sub-phase 3):
  ```yaml
  reg.<mod>.<EntityName>:
    kind: entity
    description: "<from entity candidate notes>"
    fields: {}   # populated by forge-atom; each field: {type, nullable, description}
    changelog:
      - version: "0.1.0"
        date: <YYYY-MM-DD>
        change_type: added
        description: "Stub created by forge-discover. Fields populated by forge-atom."
  ```

- **Errors and constants remain deferred.** "We'll define errors and constants when specific atoms force them."

**Outputs.** `L0_registry.yaml` with populated `naming_ledger`, `error_categories`, `external_schemas`, `side_effect_markers`; preliminary `types` stubs for qualifying entities using `reg.<mod>.<TypeName>` ids and empty `fields: {}`; empty `errors: {}` and `constants: {}`.

**Exit condition.** Human has confirmed or deviated on each of the four skeleton sections. Entity stubs written for qualifying entities. File validates against the L0 schema's skeleton requirements.

**Transition to sub-phase 4.** "Good. Now project-wide defaults every atom will inherit."

---

### Sub-phase 4 — Project conventions (L1)

**Purpose.** Set atom-level defaults — retry policy, logging, security posture, verification floors, audit triggers, idempotency, overrides.

**Entry trigger.** L0 skeleton done.

**Primary shapes.** Defaulting (dominant), prioritization, probing.

**Seed questions:**
- "For each error category from L0 — what's the default failure action? return_to_caller, retry, halt_and_alert, dead_letter, circuit_breaker?"
- "Default log level? Template strings for entry/success/failure lines?"
- "Authentication methods your system supports? Role taxonomy?"
- "Verification floors: minimum property_assertions, edge_cases, example_cases per atom?"
- "Audit triggers — which side-effect markers should force an audit log row?"
- "Idempotency — which markers require an idempotency key? Dedup strategy?"
- "Which L1 fields may atoms override? Require justification?"

**Adaptation rules:**
- If sub-phase 0's pain involves reliability (data loss, failed transactions) → propose stricter failure defaults: more retries on NET, `halt_and_alert` on DAT, higher verification floors.
- If sub-phase 0 shape is "tool someone opens daily" (consumer-facing) → propose INFO as default log level with verbose templates.
- If sub-phase 0 surfaced regulatory constraints → propose audit triggers on all WRITE markers + CALLS_EXTERNAL; require ownership checks on WRITES_DB.
- Use only error categories from sub-phase 3 — don't propose defaults for categories that don't exist.

**Techniques:**
- **Propose a full draft L1.** Based on the example fixture plus domain signals. Show the human the whole draft. Ask: "Section by section, anything to deviate from?"
- **Interrogate only on deviation.** If the human says "looks good," move on fast. Don't re-interview fields the human is happy with defaults for.

**Outputs.** `L1_conventions.yaml` committed.

**Exit condition.** Human has accepted or modified each of the seven L1 sections. File validates.

**Transition to sub-phase 5.** "Last piece — platform-level posture."

---

### Sub-phase 5 — Platform & runtime posture (L5)

**Purpose.** Set deployment platform (cloud, region, compute), rollout strategy, rate-limiting, and event semantics. This sub-phase contains the **highest concentration of critical decisions** in the entire discover process — several of them must be surfaced as option sets rather than defaults.

**Entry trigger.** L1 done.

**Primary shapes.** Option-set presentation (for criticals), defaulting (for routines), prioritization.

**Structure — two layers:**

**Layer 1 — Platform (critical; present options if not signaled)**

Seed questions and option-set behavior:

- **Cloud provider.** If the human hasn't mentioned one in sub-phases 0–2, present the option set from Section 2a's example. If mentioned (e.g., "we're on AWS"), confirm only.
- **Primary region + multi-region posture.** "Primary region? Single-region or multi-region?" For multi-region, probe driver: "What's forcing multi-region — latency, disaster recovery, or data residency?" Each driver leads to different downstream implications.
- **Default compute model.** Present as option set:
  > Your options for default compute, given [cloud]:
  > 1. **Serverless functions** (Lambda / Cloud Functions / Azure Functions) — lowest ops. Best for event-driven, bursty workloads. Cold-start cost.
  > 2. **Managed containers** (ECS Fargate / Cloud Run / Container Apps) — hybrid. Best when you want containers without Kubernetes.
  > 3. **Kubernetes** (EKS / GKE / AKS) — maximum control. Best if you have k8s expertise or complex networking.
  > 4. **Long-lived VMs or instance groups** — simplest mental model. Best when the other three genuinely don't fit.
  >
  > Which fits, and why?
- **Primary persistence model.** Present as option set if not already decided through module discussion:
  > 1. **Relational (Postgres / MySQL / Aurora)** — ACID, joins, schema migrations. Default for most business apps.
  > 2. **Document (Mongo / DynamoDB / Firestore)** — flexible schema, single-row scale. Good for user-generated content, catalog data.
  > 3. **Key-value (DynamoDB / Redis)** — high throughput, simple access patterns. Good for sessions, caches, feature flags.
  > 4. **Mixed** — different modules use different stores. Common at scale; adds consistency complexity.

**Layer 2 — Runtime posture (mostly routine; some criticals)**

- **Environments** (routine): "Environments: dev, staging, prod — anything else? (e.g., 'qa', 'sandbox')"
- **Deployment strategy** (critical; option set if not signaled):
  > 1. **Rolling** — simplest; good default unless you have specific risk concerns.
  > 2. **Canary** — stages traffic incrementally. Best if you have metrics-driven rollout and instrumentation to detect regressions.
  > 3. **Blue-green** — zero-downtime cutover. Best for stateless apps with fast rollback needs.
  > 4. **Recreate** — tear down and redeploy. Only for non-critical workloads or breaking changes.
- **Rate limits** (routine, defaults by auth method).
- **Event delivery semantics** (critical; option set):
  > 1. **At-most-once** — simplest; events may be lost. Fine for metrics, telemetry.
  > 2. **At-least-once** — events never lost but may duplicate. Default for business events; requires idempotency on all consumers.
  > 3. **Exactly-once** — no loss, no duplicates. Most expensive; requires coordinated infrastructure. Usually only justified when duplicate delivery has serious consequences (money movement, inventory changes, safety-critical actions).

**Adaptation rules:**
- If sub-phase 0's pain involved data consistency or transactional integrity → lean toward exactly-once or at-least-once with strict idempotency; surface this bias when presenting options.
- If sub-phase 0's shape is "background service" or "scheduled workflow" → rate limiting matters less; ordering likely matters more.
- If the project is low-latency or real-time → propose tighter rollback criteria and lower latency thresholds.
- If external integrations (sub-phase 3) have strict rate limits → propose conservative outbound rate limits to match.
- If sub-phase 0 surfaced regulatory or compliance constraints → restrict cloud options to those that meet them (signed agreements, certifications); note each constraint in the option set's "best for" lines.
- **After the cloud and compute decisions are made**, revisit any `L2_modules/*.yaml` that were drafted without `managed_services` (because the cloud wasn't decided yet) and ask: "For module [X], which managed services does it use now that we're on [cloud]?"

**Observability** (routine; batch with other routine decisions):
- Stack: "What observability backend does this project use?" (no default — record whatever the team has chosen; free-form string)
- Defaults: propose `latency_p99_ms: 500`, `error_budget_percent: 1.0`, `trace_sample_rate: 0.1`. Adjust by domain: latency-critical services → 200ms default; high-error-tolerance background workers → 2.0%.
- Per-module SLAs: for each L2 module confirmed so far, propose a latency budget based on its description and system shape. Present as a table — human adjusts any row.
- Leave `metrics`, `alerts`, and `atom_overrides` empty at discover time. These emerge during `forge-atom` when the atom's contract surface makes them obvious.

**Adaptation rules:**
- If sub-phase 0 involved payments, financial transactions, or safety-critical flows → propose tighter SLA defaults (200ms p99, 0.5% error budget) and higher trace sample rates (0.5 default).
- If sub-phase 0 shape is "background service" → relax latency defaults (1000ms), tighten error budgets (0.1%).
- If the team has already mentioned a specific observability stack → use it as `stack` verbatim without asking again.

**Outputs.** `L5_operations.yaml` committed with `deployment.platform`, `deployment` rollout, `rate_limiting`, `event_semantics`, and `observability` (stack + defaults + per-module SLA stubs) all populated.

**Exit condition.** File validates. All modules' `tech_stack.managed_services` are populated (no deferred ones remain in `open_questions`).

**Transition to handover.** "Ready to start breaking modules into atoms? I'd recommend starting with [X] because it's the one you said was hardest to get right."

---

## 6. State detection protocol

At entry, the skill inspects the spec directory and decides which sub-phase to resume at:

| Observed state | Entry sub-phase |
|---|---|
| No `supporting-docs/discovery-notes.md`, no spec dir | **0** |
| `supporting-docs/discovery-notes.md` exists, thesis/user/pain/fence incomplete | **0** (resume where blank) |
| `supporting-docs/discovery-notes.md` complete through fence; no capability inventory | **1** |
| Capability inventory exists; no `L2_modules/*.yaml` | **2** |
| L2 modules exist; no `L0_registry.yaml` | **3** |
| L0 skeleton done; no `L1_conventions.yaml` | **4** |
| L1 done; no `L5_operations.yaml` | **5** |
| All artifacts present and valid | Recommend `/forge-decompose <CODE>` |

When the forge CLI is available, the skill uses `forge list` to read state. When unavailable, it reads the YAML files directly.

---

## 7. Revision protocol

At any sub-phase, the human can say "let's revise [X]" — module boundaries, a conventions section, the thesis itself.

The skill:
1. Reads the current state of the relevant artifact(s).
2. Walks the human back to the relevant sub-phase — but starts from the current content, not from blank.
3. Updates the file incrementally as revisions are confirmed.
4. **Checks downstream consistency.** A sub-phase 2 module split may require re-allocating `external_schemas` in sub-phase 3's L0 skeleton, or updating module references in `L1_conventions.yaml` overrides. Flag these and offer to handle them.

Revision is cheap because the domain model is preserved. The agent does not start over; it adjusts.

---

## 8. Termination

`forge-discover` terminates when **all** of the following are true:

- `supporting-docs/discovery-notes.md` exists with the full sub-phase 0/1 structure filled.
- At least one `L2_modules/*.yaml` exists and validates.
- `L0_registry.yaml` skeleton exists and validates.
- `L1_conventions.yaml` exists and validates.
- `L5_operations.yaml` exists and validates.
- The human confirms no further revisions right now.

At termination, the skill:

1. **Summarizes** what was produced — file inventory, module count, key decisions.
2. **Recommends** which module to decompose first. Heuristic: the module covering the capability the human named as "hardest to get right" in sub-phase 1.
3. **Hands off** to `/forge-decompose <CODE>`, or returns control to the human to invoke it manually.

---

## 9. What `forge-discover` does NOT produce

This is as important as the output list. The skill deliberately stops short of:

| Not produced | Reason |
|---|---|
| Atoms (`L3_atoms/*.yaml`) | `forge-decompose` does this — the decomposition is its own interview |
| Types (`L0.types`) | Emerge from atom input/output shapes; premature definition creates cruft |
| Errors (`L0.errors`) | Emerge from atom failure modes; categories alone are enough at this stage |
| Constants (`L0.constants`) | Emerge from atom logic; almost always atom-specific |
| Policies (`L2_policies/*.yaml`) | Emerge when sensitive atoms exist to govern |
| Flows or journeys (`L4/*.yaml`) | Emerge when atoms exist to compose |

Everything `forge-discover` produces is scaffolding every atom will later reference. Nothing is atom-specific. This is enforced, not a suggestion — producing atom-level artifacts in discover means guessing, and guessing propagates as spec rot.

---

## 10. Artifact schemas

### `supporting-docs/discovery-notes.md` — canonical structure

```markdown
# Discovery notes — <project name>

Last updated: <YYYY-MM-DD>

## Product thesis
<one paragraph — the distilled "what" and "for whom">

## Target user
<specific enough to imagine one person by name>

## Pain / job-to-be-done
<concrete, with a scenario — not an abstraction>

## Delta vs. status quo
<what's meaningfully better, and for whom>

## Shape
<tool | service | workflow | platform — one line>

## Success signal
<how you'll know this worked at month 6>

## Scope fence
<what's explicitly not in scope; who is not a target user>

## MVP cut
<the 2-week version, if forced>

## Typical user session
<narrative walkthrough in the user's vocabulary>

## Capability inventory
- <capability 1>
- <capability 2>
- ...

## External integrations observed
- <service — purpose — auth method>

## Change axes
- Weekly: <what changes often>
- Yearly: <what's stable>

## Critical failure modes
- <failure — consequence>

## Module map
<ASCII diagram — modules and dependency arrows>

## Domain model
```yaml
actors: [...]
nouns: [...]
verbs: [...]
pains: [...]
constraints: [...]
vocab: {...}
comparisons: [...]
open_questions: [...]
```

## Open questions
- <things the human was unsure about — to revisit in later skills>
```

### L2 module file — minimum shape at discover exit

```yaml
module:
  id:          <3-letter code matching naming_ledger.module_id>
  name:        <human-readable>
  description: |
    <specific, not generic — say what this module owns and why it exists as a boundary>
  tech_stack:
    language:            <string>
    language_version:    <string>
    runtime:             <string>
    runtime_version:     <string>
    frameworks:          []
    mandatory_libraries: []
    compute:             <string>            # optional; overrides L5.deployment.platform.default_compute
    managed_services:                         # cloud-managed services this module depends on
      - service:  <string>                    # e.g., aws-rds, aws-sqs, azure-sql, gcp-bigquery
        purpose:  <string>                    # one line — what it's used for
  owned_atoms:     []        # populated by forge-decompose
  owned_artifacts: []        # populated by forge-decompose
  persistence_schema:
    datastores:      []          # populated by forge-decompose / forge-atom
    storage_buckets: []
    caches:          []
    ownership:       exclusive
    shared_with:     []
  interface:
    entry_points: []         # populated by forge-decompose / forge-atom
  access_permissions:
    env_vars:         []
    filesystem:       []
    network:          []
    secrets:          []
    external_schemas: []
  dependency_whitelist:
    modules: [<other module codes>]
  policies: []
  changelog:
    - version:     "0.1.0"
      date:        <YYYY-MM-DD>
      change_type: added
      description: "Initial module from forge-discover."
```

### L0 skeleton — minimum shape at discover exit

`naming_ledger`, `error_categories`, `external_schemas`, `side_effect_markers` populated. `errors`, `types`, `constants` are present as empty maps.

### L1 and L5 — full files

All sections populated (see L1 and L5 schema docs in `docs/framework-overview.md` or the `src/templates/` schema files).

---

## 11. Compatibility with skill formats

This framework is format-agnostic. To ship it as a runnable skill:

**agentskills.io format** — `.agents/skills/forge-discover/SKILL.md` with frontmatter + condensed body referencing this framework. The SKILL.md body contains the directive instructions; the framework doc is bundled under `references/framework.md` and loaded on demand for adaptation rules and question taxonomy.

**Claude Code skill** — same structure, same file layout. agentskills.io format works natively.

**Human-facilitated workshop** — the framework is the facilitator's script. They run the interview using the question shapes and adaptation rules; the outputs are the same YAML files any AI implementation would produce.

---

## 12. Open design questions (for future iterations)

- **Does the framework benefit from a `--strict` mode?** Forcing the human to answer every adaptation-generated question, even if they'd rather skip. Default is lax.
- **Should the domain model be typed?** Right now it's free-form YAML. A typed schema would let the agent reason about it more reliably but imposes a naming discipline on the human upfront.
- **Recovery from bad sub-phase 0.** If the thesis turns out to be wrong halfway through sub-phase 2, the skill should detect it — "the module you just described doesn't fit the thesis" — and surface it. Not yet defined.
- **Multi-session continuity.** Right now the skill resumes from disk state. If the conversation crosses sessions with different agents, does the domain model transfer cleanly? Probably yes via `supporting-docs/discovery-notes.md`, but untested.
