# forge-audit — Framework

This document describes the **mental model** for `forge-audit`: the role-shift from creator skills to challenger skill, the nine audit passes, the severity model, historical tracking, batch-review mechanics, and contract materialization gate. It is **not** the SKILL.md; it is the source of truth from which any skill artifact is authored.

Audiences:
- An LLM or agent that executes the process
- An engineer authoring the `SKILL.md` from this framework
- A human facilitator running audit without an AI

---

## 1. What `forge-audit` is

**Purpose.** Stress-test completed specs for gaps, contradictions, drift, risk, and contract ambiguity — **before implementation begins**. Not a creator skill; a challenger skill. Reads the spec corpus (or a requested scope), runs nine audit passes, compiles a severity-ranked findings report with proposed inline edits, lets the human approve/skip edits in batch, escalates persistent findings across runs, and emits a canonical native-language contract artifact on clean pass.

**Role contrast with the three creator skills:**

| | discover / decompose / forge-atom | **forge-audit** |
|---|---|---|
| Role | Interviewer (Socratic, extractive) | Challenger / reviewer (adversarial) |
| Writes | Creates specs | Edits existing specs (clarifications, added edge_cases, policy proposals) |
| Primary output | Spec files | Audit report + inline spec edits |
| Interview feel | Elicitation | Code-review |
| Invocation scope | One atom / module | Project-wide default, narrowable |
| Question shape | "What does this do?" | "What's wrong with this?" |

**Specific outputs at exit:**

| Artifact | Contains | Purpose |
|---|---|---|
| `supporting-docs/audit-YYYY-MM-DD.md` (new each run) | Full findings list with evidence, severity, proposed edits, approval status | Durable record of this audit's state |
| `supporting-docs/audit-history.md` (maintained across runs) | Every finding ever surfaced with persistence count, resolution status | Enables severity escalation for recurring findings |
| `contract/<lang>/...` (on clean full-tier run) | Canonical native-language signatures, structs, seams, and error-return declarations | Removes signature drift before `forge-implement` |
| Edited spec files (conditional on human approval) | Added `edge_cases`, corrected `side_effects`, aligned drift, updated changelogs | Applies fixes that resolve findings |

---

## 2. Operating principles

Inherits the universal principles — one concept per turn (during interactive review), confirm before writing, cite specific references by name. Specific to audit:

1. **Challenger, not creator.** Audit never creates new atoms, types, errors, constants, modules, flows, or journeys. If a finding *needs* a new entity, the audit's proposed fix is to **route the human back** to the appropriate creator skill (e.g., "create missing atom via `/forge-decompose` then `/forge-atom`").
2. **Severity is proposed, not enforced.** Agent assigns severity from heuristics (§5). Human may disagree during review; the skill respects the human's override.
3. **Batch presentation, individual approval.** Findings are compiled into one report, presented in one summary, but human approves edits one-by-one (or en bloc by severity class). Never apply edits without explicit approval.
4. **Historical awareness escalates recurring findings.** An issue flagged three audits in a row moves up a severity tier. The rationale: if it's still there after multiple gates, it's become a real risk, not an artifact.
5. **Report file is the canonical artifact.** Whatever the chat summary says, the report file is the authoritative record. Links from history back to specific reports must stay valid.
6. **Auto-triggered audits announce and defer.** When audit fires automatically (after the last atom of the last module is elicited), it compiles the report and summarizes in chat with a deferrable engagement prompt — never blocks forward motion by forcing immediate review.
7. **Scope adapts to what's complete.** Manual audits with no `--scope` run against whatever specs exist; auto-triggered audits are project-wide because by definition all atoms are elicited by that point.

---

## 3. When it runs

### Manual invocation

- `/forge-audit` — project-wide scope (default), full tier (both quick passes 1–5 AND risk/policy/contract passes 6–8)
- `/forge-audit --scope <module>` — scope narrowed to one module
- `/forge-audit --scope <atom>` — scope narrowed to one atom (useful for spot-checking after revision)
- `/forge-audit --tier quick` — only passes 1–5 (completeness + consistency + hygiene + reachability), skip the slower risk interrogation, policy coverage, inter-atom contract verification, and contract materialization passes

### Auto-trigger

Fires exactly once per project: at the completion of the last atom of the last unfilled module. Concretely: after `forge-atom` writes a stub's spec and detects that `forge list --kind atom --ids-only` has zero atoms with empty `spec` blocks remaining. The triggering skill announces:

> *"All project atoms are now elicited — auto-triggering project-wide full audit."*

Auto-trigger characteristics:
- **Scope**: project-wide (guaranteed by the trigger condition)
- **Tier**: full (this is the implementation gate)
- **Interactivity**: report generated, chat summary presented, human chooses engage-now vs defer. Never blocks.

### Tier selection logic

- **Quick tier** (passes 1–5): fast sanity check, ~10–30 s of tool use. Use for mid-project check-ins, spot-checks after spec revisions, or when the human just wants "any obvious problems?"
- **Full tier** (passes 1–9): thorough pre-implementation gate, ~30–90 s. Use for the auto-trigger, end-of-project review, or when the human explicitly asks for an exhaustive audit.

Agent defaults to full tier for manual invocation unless the human passes `--tier quick` or the scope is a single atom (in which case quick is fine — risk interrogation, policy coverage, and contract proof are project-wide concerns).

---

## 4. The nine audit passes

Each pass is a deterministic scan against the spec corpus. Findings accumulate; severity is assigned per pass's heuristics.

### Pass 1 — Completeness (quick tier)

**What it detects:** specs that don't satisfy their own structural requirements.

**Checks:**
- For each atom in scope: `forge context <atom>` exit status. Exit 2 (unresolved refs) → **blocking** finding with the list of unresolved ids.
- For each atom: required fields per `kind` are present (PROCEDURAL must have `input`, `output`, `side_effects`, `invariants`, `logic`, `failure_modes`; DECLARATIVE must have `target`, `desired_state`, `reconciliation`; etc.). Missing required fields → **blocking**.
- For each atom: verification floors met per L1. `property_assertions` below `L1.verification.floors.min_property_assertions` → **high**. Same for edge_cases and example_cases.
- For each atom: changelog has at least one entry with a valid date. Missing → **medium**.

### Pass 2 — Internal consistency (quick tier)

**What it detects:** contradictions within a single atom's spec.

**Checks:**
- **side_effects vs. logic.** Parse `logic` for action keywords: if logic contains `INSERT/UPDATE/DELETE` but `side_effects` lacks `WRITES_DB` → **high**. If `EMIT <event>` but no `EMITS_EVENT` → **high**. If `CALL external.<x>.<y>` but no `CALLS_EXTERNAL` → **high**. If `READ FROM <table>` but no `READS_DB` → **medium**.
- **invariants reference declared fields only.** Every field path in `invariants.pre` and `invariants.post` must exist in the atom's `input` or `output.success`. Undefined field references → **high**.
- **failure_modes ↔ output.errors.** Every error in `output.errors` should appear in at least one `failure_modes` trigger (reverse: every `failure_modes.error` should be in `output.errors`). Asymmetry → **high**.
- **logic path coverage.** Every error code returned via `RETURN <error>` should exist in `output.errors`. Escape hatches return codes not declared in output.errors → **high** (silent failure surface).

### Pass 3 — Cross-spec consistency (quick tier)

**What it detects:** contradictions between atoms, or between atoms and their surrounding constraints. Same seven check classes as forge-atom's consistency probes, but run across *every atom in scope*.

**Checks (the forge-atom seven, applied project-wide):**

| # | Check | Project-wide form |
|---|---|---|
| 3a | Policy | For every policy × every atom in applicable module: evaluate `applies_when`; verify `mandatory_behavior.before/after_success/after_failure` is honored in atom's logic |
| 3b | Sibling atom | Within each module: cross-reference invariants that touch shared types for contradictions |
| 3c | Called-atom contract | For each atom in scope, load `forge context <id>` and read `called_atom_signatures` — the bundle already contains `input`, `output`, and `side_effects` for every atom it calls. Four checks must all pass: (a) every non-nullable callee `input` field is explicitly bound or forwarded, (b) the type at each bound position matches the callee's declared input type by L0 id or structural field equivalence (field names, types, nullability), (c) every error code in callee `output.errors` is covered by a TRY/CATCH branch in the caller, (d) every callee `output.success` field read by the caller exists in the callee's signature with compatible type and nullability |
| 3d | L1 convention | For every atom: declared markers vs L1 `security.resource_authorization`, `audit.triggers`, `idempotency.key_source` |
| 3e | Access-permission | For every `external.X.*`, `env.X`, network call in atom logic: verify against module's `access_permissions` whitelist |
| 3f | Type invariant | For every atom producing a typed output: check logic branches don't produce values that violate the output type's invariants |
| 3g | Event contract | For every `EMIT <event>`: compare emitted payload shape to consumers' declared expected payload types |

**Severity:** 3a/3c/3d → **blocking** (policy violations and contract breaks cause real bugs). 3b/3f/3g → **high**. 3e → **blocking** if access is missing (schema-level violation). For 3c: any of the four sub-checks failing is **blocking**.

### Pass 4 — L0 hygiene (quick tier)

**What it detects:** unused, near-duplicate, or drifted L0 entries.

**Checks:**
- **Orphan types.** For each `L0.types` entry: count consumers (atoms referencing it via input, output, invariants, logic field paths; tables referencing it via `datastores[].type`). Zero consumers → **medium** ("orphan type — consolidate with existing or delete").
- **Orphan errors.** For each `L0.errors` entry: count atoms that return it via `output.errors` or `failure_modes.error`. Zero → **medium**.
- **Orphan constants.** For each `L0.constants` entry: count references in atom logic/invariants. Zero → **medium**; single consumer → **low** ("consider demoting to local value").
- **Near-duplicate types.** For types with same `kind: entity`: compute field-set Jaccard similarity. ≥0.8 overlap and names are different → **medium** ("consider consolidating `reg.X.Y` and `reg.X.Z`").
- **Near-duplicate errors.** Errors in the same category whose `message` has high text similarity → **low**.
- **Type drift.** For each atom in scope: inspect inline field declarations in `input`, `output.success`, and `props` for fields that represent the same logical entity but are declared differently across atoms (e.g., one atom has `input.user_id: string` while another has `input.customer: { id: string }` for the same user concept). Flag as **high**: "type drift — `<entity>` described differently in `<atom_a>` and `<atom_b>`; consider converging on a shared L0 type."
- **L0 id drift.** For every CALL edge in scope: if the type passed at a call site uses a different L0 id from the callee's declared input type but shapes are structurally equivalent → **high** ("L0 id drift — align to one shared type"). If shapes are structurally incompatible → **blocking**.

### Pass 5 — L4 reachability (quick tier)

**What it detects:** atoms that exist but are never invoked.

**Checks:**
- Build the invocation graph: for each atom, note which atoms CALL it (from logic) and which entry_points invoke it (from L2 `interface.entry_points[].invokes`) and which flow/journey sequences reference it.
- For each atom: determine if reachable from any entry point via the invocation graph.
- Unreachable atoms → **high** ("dead code: defined but never invoked").
- **Exception**: compensation-only atoms (referenced only as `compensation:` in saga flows, never as `invoke:`) are reachable and flagged as **informational/low** (not high), since they exist for a structural reason.

### Pass 6 — Risk interrogation (full tier)

**What it detects:** atoms that have implicit risk profiles their specs don't address.

**Checks (per-atom adversarial probes):**
- **Concurrency safety.** Atoms with `WRITES_DB` on a datastore that other atoms also write to: does the spec address concurrent-modification semantics (optimistic locking, row-level locks, CAS, version columns)? Missing → **high**. Surface as a proposed `edge_case`.
- **Partial-failure recovery.** Atoms with ≥2 side-effect markers (e.g., WRITES_DB + CALLS_EXTERNAL): does the spec address what happens when the first effect succeeds and the second fails? Missing → **high**.
- **Idempotency.** Atoms with `CALLS_EXTERNAL` + `WRITES_DB`: is there an idempotency key declared? Does the caller flow retry? If retry expected and no idempotency key → **blocking** (directly causes bugs under retry).
- **Cache staleness.** Atoms with `READS_CACHE`: does the spec address how stale reads are handled? Missing → **medium**.
- **Clock skew.** Atoms with `READS_CLOCK`: does the spec tolerate clock drift, or assume wall-clock correctness? Missing → **low** (often fine, but worth flagging).

Findings proposed as new `edge_cases` or new `property_assertions` with specific wording.

### Pass 7 — Policy coverage (full tier)

**What it detects:** atoms whose side-effects warrant governance no policy provides.

**Checks:**
- **Sensitive markers unguarded.** For each atom with "sensitive" markers — heuristics: `WRITES_DB` on datastore containing type names like `Charge`, `Payment`, `Credential`, `Session`, `Token`; `CALLS_EXTERNAL` to payment providers (Stripe/Braintree/etc. recognized from L0 `external_schemas`); atoms writing PII fields (email, ssn, phone) — check if any policy in the module's `policies` list has an `applies_when` that matches this atom. Unguarded sensitive atoms → **high** (not blocking because absence of policy doesn't mean absence of security; it means absence of *documented* security).
- Propose new policy scaffolds; do not create. Recommend human invokes `/forge-discover` with policy-addition scope (future work; for now, manually edit L2_policies/).

### Pass 8 — Inter-atom contract verification (full tier)

**What it detects:** caller/callee boundaries that look plausible in prose but are not actually contract-compatible.

This pass is intentionally stricter than Pass 3c. Pass 3c verifies that a caller covers the callee's failure surface. Pass 8 verifies the full atom-to-atom handoff: inputs, outputs, nullability, structured primitives, enum/discriminator branches, and edge-level error assumptions.

**Edges in scope:**
- every `CALL <atom>` in any atom logic block
- every L4 flow `invoke` or `compensation` edge where one atom's output is bound into another atom's input
- every journey handler or transition edge that binds one atom into another

**Checks:**
- **Input coverage.** Every required callee input field must be explicitly bound, forwarded, or satisfied by a declared constant/default. Missing binding → **blocking**.
- **Type identity or structural proof.** When a caller passes a typed value into a typed callee field, either the L0 type IDs match exactly or the normalized field maps are identical with compatible nullability. Similar-looking types do not count. Mismatch → **blocking**.
- **Primitive shape compatibility.** If either side uses `shape` on a primitive, compare the actual structure, not just presence of the field. Enum values, discriminator keys, variants, patterns, and JSON-schema shape must all be compatible. Divergence or ambiguity → **blocking**.
- **Output consumption proof.** Any caller logic that reads `callee.output.success.<path>` or branches on it must reference a field that exists on the callee success contract with compatible type/nullability/shape. Missing or incompatible field → **blocking**.
- **Enum / discriminator narrowing.** If caller logic assumes a particular enum member or tagged-union branch from callee output, that branch must be declared by the callee. Assumed-but-undeclared branch → **blocking**.
- **Opaque pass-through discipline.** A primitive without `shape` may only be treated as opaque pass-through. If downstream logic parses, splits, pattern-matches, or discriminates on it, missing `shape` is **blocking** even if another tool surfaced incidental structure.
- **Edge-level error alignment.** Re-run Pass 3c at the exact edge level and also compare any caller branch assumptions on error codes. Handling undeclared errors or omitting declared reachable errors → **blocking**.

**Preferred fixes:**
- align both sides to one shared L0 type id
- add or correct `shape` where the primitive is structurally consumed
- update caller logic so it stops relying on undeclared fields or branches
- if an adapter atom is truly needed, route back to `/forge-decompose` then `/forge-atom`; audit does not create it

### Pass 9 — Contract materialization (full tier)

**What it detects:** specs that are semantically valid but still ambiguous when translated into native-language code.

**Inputs:**
- full spec corpus
- target implementation language from `L1_conventions.implementation.primary_language` when available
- deterministic mapping rules from `assets/type_mapping/<lang>.yaml`

**Materialization work:**
- derive function signatures for atoms / flows / journeys
- derive request/result structs
- derive seam declarations from side-effect markers
- derive native error-return form

**Determinism checks:**
- every field maps to exactly one native type rule
- every primitive field that downstream atoms parse structurally has `shape` or an equivalent explicit format reference
- every side-effect marker resolves to one seam idiom
- every `failure_modes.error` resolves to an L0 sentinel
- every atom `CALL` site is signature-compatible after materialization
- every flow invoke binds compatible parameter types after materialization

**Severity:** any materialization ambiguity is **blocking**.

**Output on clean pass:**
- `<spec-dir>/contract/<lang>/index.yaml`
- one contract file per module
- one per flow package
- one per journey package

These files become the canonical contract downstream skills consume. `forge-implement` treats absence or staleness as a hard stop.

### Pass orchestration

Passes run in order 1 → 9. Each pass produces findings that may reference findings from prior passes (e.g., a Pass 3 policy check may surface in more detail because Pass 1 flagged the atom as incomplete). Pass 9 only emits contract artifacts when no blocking issues remain, and only after Pass 8 has proven every explicit atom boundary is contract-compatible. The skill assembles findings with stable IDs (e.g., `FND-001`, `FND-002`) and cross-references where applicable.

---

## 5. Severity model

Four tiers with clear semantics:

| Severity | Meaning | Examples |
|---|---|---|
| **Blocking** | Implementation cannot proceed without resolution — the spec is incorrect or incomplete in a way that will cause bugs | Unresolved atom references; missing idempotency key on retry-expected atom; policy violations; schema-invalid spec |
| **High** | Strong recommendation to fix — the spec will work but has material quality issues | Verification floor not met; sibling drift; orphan types in active modules; dead atoms |
| **Medium** | Worth reviewing before implementation — not wrong, but suboptimal | Near-duplicate types; constants with single consumer; missing edge_case for known concurrency pattern |
| **Low** | Informational — stylistic or minor hygiene | Changelog date format inconsistency; near-duplicate error messages; policy-proposable atom in non-sensitive path |

### Severity escalation from history

When a finding appears in `supporting-docs/audit-history.md` from a prior run:
- Same finding flagged in 2 consecutive audits → bump severity one tier (low → medium → high → blocking)
- Same finding flagged in 3+ consecutive audits → escalate with explicit note: *"this finding has persisted across N audits. Escalating to blocking."*

Rationale: if an issue survives multiple gates without being addressed, it's becoming an ambient risk. Escalation forces attention.

### Severity override

When the human engages with findings during interactive review, they may override the agent's severity:
- *"This `medium` is actually blocking — we can't launch without fixing it."* → agent re-tags.
- *"This `blocking` is a known acceptable risk for now — demote to medium."* → agent re-tags and records rationale in `supporting-docs/audit-history.md`.

Overrides are recorded in the audit report and in history so subsequent audits know.

---

## 6. Historical tracking — `supporting-docs/audit-history.md`

Persistent record of every finding ever surfaced, with resolution status.

**Purpose:**
- Enable severity escalation for persistent findings.
- Give the human a long-term view of spec quality trends.
- Avoid re-surfacing findings the human has explicitly marked as known risks (future work — for now, recording only, no filtering).

**Structure:** see §10 for schema. Each finding has a stable ID across runs (hashed from scope + pass + location + fingerprint), status (open / resolved / known-risk), and a run history showing when it was flagged and with what severity.

**Maintenance:**
- On each audit run: for each finding in the new report, look up by stable ID in history.
  - New finding → add entry with `status: open`, initial severity, this run's report link.
  - Recurring finding → append to run history, check persistence count for escalation.
  - Previously-resolved finding that reappears → flag: *"this was resolved in audit-<date>; it's back. Regression?"*
- On fix application: when a proposed edit is approved and applied, mark the corresponding finding as `resolved` in history, record the resolution commit/changelog reference.

---

## 7. Sub-phase structure

### Sub-phase 0 — Scope + tier + state load

- Parse invocation: manual flags (`--scope`, `--tier`) or auto-triggered.
- Load `supporting-docs/audit-history.md` if it exists.
- Run `forge list --spec-dir <dir>` to count atoms, modules, L0 entries — establishes baseline counts.
- Announce: *"Running forge-audit. Scope: `<scope>`. Tier: `<quick|full>`. `<N>` atoms in scope."*

### Sub-phase 1 — Execute passes

- Run selected tier's passes (1–5 or 1–9) in order.
- Each pass emits a list of findings with: stable ID, pass number, location, description, evidence, proposed severity, proposed fix (if applicable).
- Cross-reference findings with history: escalate persistence, flag regressions.

### Sub-phase 2 — Compile report

- Sort findings by severity (blocking → high → medium → low) within each pass.
- Generate `supporting-docs/audit-YYYY-MM-DD.md` following the template in §10.
- Chat summary: *"Audit complete. `<N>` findings (`<K>` blocking, `<H>` high, `<M>` medium, `<L>` low). Report at `<path>`."*

### Sub-phase 3 — Interactive review (conditional)

Human chooses: engage now, or defer until later.

If engage:
1. Agent walks findings in severity order (blocking first, always).
2. For each finding:
   - Show finding, evidence, proposed edit (with diff preview if applicable).
   - Human options: `approve` / `skip` / `defer` / `override-severity`.
   - Approve → agent applies edit (writes to spec file with changelog entry). Marks finding `resolved` in history.
   - Skip → leaves finding open. Next audit will re-flag.
   - Defer → same as skip, but tagged `deferred-<date>` so human sees they've been sitting.
   - Override-severity → re-tag; continue review.
3. After final finding: summarize resolutions.

If defer:
- Report file is preserved.
- Next time human runs `/forge-audit`, skill detects the prior unreviewed report and asks: *"Found unreviewed audit from `<date>`. Review that before running a new one?"*

### Sub-phase 4 — Handover

- Update `supporting-docs/audit-history.md` with all findings' statuses.
- Record `contract_root`, `contract_hash`, and generated file hashes when Pass 9 succeeds.
- **If blocking findings remain open:** *"Implementation should not proceed. `<K>` blocking findings remain. Resolve before running `/forge-implement`."*
- **Else:** *"Ready for implementation. `<N>` non-blocking findings remain; address when convenient. Next: `/forge-implement`."*

---

## 8. Batch review mechanics

"Batch" means: the report is assembled once and presented as a whole, but individual findings require individual approval. Three variants during review:

**Interactive sequential** (default):
Walk each finding in severity order. Human approves/skips/defers per finding.

**Bulk-approve by severity**:
Human can say: *"approve all `low` severity en bloc"* or *"approve all with `auto-fixable: true` tag"*. Agent applies the set, reports outcomes, continues with remaining findings.

**Review-only**:
Human reads the report, makes no decisions. All findings stay `open` in history. Re-enter interactive review any time with *"resume audit review"* — agent picks up from the report's unresolved items.

---

## 9. What `forge-audit` does NOT produce

| Not produced | Why |
|---|---|
| New atoms | Creating atoms is decompose/forge-atom's job; audit routes the human back |
| New types / errors / constants | forge-atom creates these during elicitation; audit can propose consolidations but never creates |
| New modules | Discover's job |
| New policies | Policy creation is a future skill (policy-elicitation) or manual edit; audit proposes the scaffold in findings but doesn't write policy files |
| New flows / journeys | Composition-level; outside audit's scope |

The enforced discipline: **audit clarifies and gates; it does not create.**

---

## 10. Artifact schemas

### `supporting-docs/audit-YYYY-MM-DD.md` — report file

```markdown
# forge-audit report — <scope> — <tier>

Generated: <ISO-8601 timestamp>
Scope: <project-wide | module:<MOD> | atom:<atom_id>>
Tier: <quick | full>
Atoms scanned: <N>
Passes run: <list>

## Summary

<K> findings total
- <K_b> blocking
- <K_h> high
- <K_m> medium
- <K_l> low

<optional one-line state: "Ready for implementation" | "Blocking findings present — hold implementation">
Contract artifact: <absent | stale | generated at <spec-dir>/contract/<lang>>

---

## Findings

### FND-001 [BLOCKING] <one-line description>

**Pass:** <N — name>
**Location:** <file:line | entity_id>
**Persisted:** <new | recurring: N audits | regression from <date>>

**Evidence:**
<excerpt or reference showing the issue>

**Proposed fix:**
<description of the fix>

<optional diff preview>
```diff
- old line
+ new line
```

**Approval status:** <pending | approved | skipped | deferred | overridden-to-<severity>>

---

### FND-002 ...

(every finding, sorted: blocking first, then high, medium, low; within a severity, sorted by pass number then alphabetically by location)
```

### `supporting-docs/audit-history.md` — persistent tracking

```markdown
# forge-audit history

Last updated: <ISO-8601 timestamp>
Total findings ever surfaced: <N>
Open: <K_open>  Resolved: <K_resolved>  Known risk: <K_known>
Latest contract root: <path | absent>
Latest contract hash: <hash | absent>

---

## <finding_stable_id> — <one-line description>

**First flagged:** <date>
**Last flagged:** <date>
**Status:** open | resolved | known-risk | regressed
**Runs:** <count>
**Severity history:** <date>:low → <date>:medium → <date>:high  (shows escalation)
**Resolution:** <if status=resolved: date + how resolved + commit/changelog ref>
**Known-risk rationale:** <if status=known-risk: why accepted, review-after date>

---

(entries for every finding ever surfaced, ordered by stable_id)
```

Stable IDs are derived as `hash(pass_number + location + finding_fingerprint)[:8]` — deterministic, so the same issue across runs gets the same ID.

---

## 11. Compatibility

Format-agnostic. The skill artifact at `.agents/skills/forge-audit/SKILL.md` references this framework under `references/framework.md` for progressive disclosure — load on demand for pass-specific detection heuristics, severity escalation rules, or report schemas.

---

## 12. Open design questions (for future iteration)

- **Auto-fixable findings.** Some findings could be auto-applied without human approval (e.g., changelog date format fixes, whitespace drift). Should audit support an `--auto-apply-trivial` flag that applies all `low` severity fixes without prompting? Current design says no — every fix needs approval. Revisit after use.
- **Policy creation from coverage gaps.** Pass 7 proposes new policies but doesn't create them. Should there be a `forge-policy` skill or should audit itself open a policy-creation sub-flow? Current design defers.
- **Cross-audit regression alerting.** If a finding was resolved in audit N, then reappears in audit N+2, that's a regression. Current design flags it visually; a future version could surface regressions at the top of the chat summary.
- **Parallel audits.** For large projects, running passes in parallel would speed up `forge-audit` significantly. Current design is sequential for simplicity.
- **Audit during elicitation.** Currently audit is post-elicitation. A future version could run lightweight passes (1, 4) continuously during forge-atom to catch issues at creation time.
