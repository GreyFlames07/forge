---
name: forge-audit
description: >
  Use this skill when the user wants to stress-test completed Forge specs
  for gaps, contradictions, drift, or risk before implementation — a
  quality gate rather than a creation skill. Activates on phrases like
  "audit the specs", "review the module", "quality-check before
  implementation", "what's wrong with the spec", "run the audit", or auto-
  triggers once at the end of the last atom's forge-atom completion
  across the whole project. Runs seven audit passes (completeness,
  internal consistency, cross-spec consistency, L0 hygiene, L4
  reachability, risk interrogation, policy coverage), produces a
  severity-ranked findings report, and applies approved inline edits to
  spec files. Does NOT create atoms, types, errors, modules, or policies
  — those are creator-skill jobs; audit clarifies and gates.
---

# forge-audit

Read the project's spec corpus, run seven audit passes, produce a severity-ranked findings report with proposed inline edits, let the human approve/skip/defer each edit, and apply approved fixes to spec files. You are a challenger skill — you never create atoms, types, errors, modules, or policies. If a finding requires creation, your proposed fix routes the human back to the appropriate creator skill.

Full mental model in `references/framework.md` (~600 lines). Load on demand:
- `§4` for pass-by-pass detection heuristics
- `§5` for severity escalation rules
- `§6` for historical tracking schema
- `§10` for report and history file schemas

Otherwise this file is self-sufficient for routine operation.

## Non-negotiables

1. **Challenger, not creator.** Never write new atoms, types, errors, constants, modules, flows, journeys, or policies. When a finding needs creation, the proposed fix is to route the human back: *"Create missing atom via `/forge-decompose` then `/forge-atom`."*
2. **Severity proposed, not enforced.** Assign severity per pass heuristics. The human may override during review; respect the override and record the rationale in `audit-history.md`.
3. **Batch presentation, individual approval.** Findings are assembled into one report, presented as one summary, but every edit requires explicit approval. Never apply edits silently.
4. **Historical awareness drives escalation.** Findings flagged in ≥2 consecutive audits escalate one severity tier. At 3+ consecutive, force the escalation with an explicit note.
5. **Report file is canonical.** Chat summary may be terse; the report file is the authoritative record. History entries link back to specific reports.
6. **Auto-triggered audits announce and defer.** Never block forward motion. Announce findings summary; let the human choose engage-now or defer-later.
7. **Scope adapts to what exists.** Manual audits with no `--scope` cover whatever's been elicited so far. Auto-triggered audits are project-wide by construction (they only fire when the last atom is done).

Full rationale: `references/framework.md §2`.

## Workflow

### Step 1 — Parse invocation + load state

**Manual invocation forms:**
- `/forge-audit` — project-wide, full tier (all 7 passes)
- `/forge-audit --scope <module>` — single module, full tier
- `/forge-audit --scope <atom>` — single atom, full tier (quick auto for single-atom scope)
- `/forge-audit --tier quick` — passes 1–5 only (skip risk interrogation + policy coverage)

**Auto-trigger:** fires from forge-atom when the last unfilled atom completes. Scope = project-wide, tier = full.

**State load:**
1. Run `forge list --spec-dir <dir>` to establish baseline counts.
2. Check for existing `audit-history.md`; parse if present.
3. Check for an unreviewed prior report (an `audit-*.md` with any findings where status=pending). If found:
   > *"Found unreviewed audit from `<date>` with `<N>` unresolved findings. Review that first, or start a new audit?"*

Announce scope + tier + atom count:
> *"Running forge-audit. Scope: `<scope>`. Tier: `<tier>`. `<N>` atoms in scope."*

### Step 2 — Execute passes

Run the selected tier's passes in order.

**Quick tier: passes 1–5.**
**Full tier: passes 1–7.**

For each pass, produce a list of findings with: stable_id (hash-derived), pass number, location (file + line or entity id), description, evidence, proposed_severity, proposed_fix.

#### Pass 1 — Completeness

For each atom in scope:
```bash
forge context <atom_id> --spec-dir <dir>
```
- Exit 2 (unresolved refs) → **blocking** finding listing the unresolved ids
- Missing required fields per kind → **blocking**
- L1 verification floors not met → **high**
- Empty changelog → **medium**

#### Pass 2 — Internal consistency

For each atom in scope:
- Parse `logic` for action keywords. Compare with declared `side_effects`:
  - `INSERT/UPDATE/DELETE` but no `WRITES_DB` → **high**
  - `EMIT <event>` but no `EMITS_EVENT` → **high**
  - `CALL external.<x>.<y>` but no `CALLS_EXTERNAL` → **high**
  - `READ FROM <table>` but no `READS_DB` → **medium**
- Every field path in `invariants.pre/post` must exist in `input` or `output.success` → **high** on any undefined ref
- Every `output.errors` code appears in ≥1 `failure_modes.trigger`; every `failure_modes.error` is in `output.errors` → **high** on asymmetry
- Every `RETURN <error>` in logic must be in `output.errors` → **high** (silent failure surface)

#### Pass 3 — Cross-spec consistency

Run the seven forge-atom consistency probes, but across every atom in scope:

| Sub-pass | What | Severity |
|---|---|---|
| 3a Policy | `applies_when` evaluated against each atom; check mandatory_behavior honored in logic | **blocking** |
| 3b Sibling atom | Within each module: contradicting invariants on shared types | **high** |
| 3c Called-atom contract | Every `CALL <atom>` covers callee's declared failure_modes | **blocking** |
| 3d L1 convention | Atom markers vs L1 `security.resource_authorization`, `audit.triggers`, `idempotency.key_source` | **blocking** |
| 3e Access-permission | `external.X.*`, `env.X`, network refs vs module's `access_permissions` | **blocking** |
| 3f Type invariant | Logic branches that produce typed output values don't violate type invariants | **high** |
| 3g Event contract | `EMIT <event>` payload shape matches consumers' expected types | **high** |

#### Pass 4 — L0 hygiene

- Count consumers per L0 type (atoms with input/output/invariants referencing it + tables with `type:` referencing it). Zero → **medium**.
- Count returners per L0 error. Zero → **medium**.
- Count references per L0 constant. Zero → **medium**; single consumer → **low** ("consider demoting to local value").
- For types with `kind: entity`: compute field-set Jaccard similarity across pairs. ≥0.8 overlap with different names → **medium** ("consider consolidating").
- Same-category errors with ≥0.8 message text similarity → **low**.

#### Pass 5 — L4 reachability

Build the invocation graph:
- Each atom's `logic` → CALLs to other atoms
- Each L2 module's `interface.entry_points[].invokes` → root nodes
- Each L4 flow's `sequence[].invoke` and `sequence[].compensation` → additional roots
- Each L4 journey's `handlers[].atom` and `transitions[].invoke` → additional roots

For each atom: check if any root path reaches it.
- Unreachable → **high** ("dead code: defined but never invoked")
- Compensation-only reachable (referenced only as `compensation:`, never as `invoke:`) → **low** (structural role — not true dead code)

#### Pass 6 — Risk interrogation (full tier only)

Per-atom adversarial probes:

- **Concurrency.** Atom has `WRITES_DB` on a datastore that ≥2 atoms write to: does spec address concurrent-modification? Missing → **high**. Propose new `edge_case`.
- **Partial failure.** Atom has ≥2 side-effect markers: does spec address "first effect succeeds, second fails" path? Missing → **high**.
- **Idempotency.** Atom has `CALLS_EXTERNAL + WRITES_DB`: idempotency_key declared? If callers retry (check L4 flow `on_error` for RETRY actions) and no key → **blocking**.
- **Cache staleness.** Atom has `READS_CACHE`: stale-read handling declared? Missing → **medium**.
- **Clock skew.** Atom has `READS_CLOCK`: drift tolerance declared? Missing → **low**.

Findings proposed as new `edge_cases` or `property_assertions` with specific wording.

#### Pass 7 — Policy coverage (full tier only)

Sensitive-atom heuristics (any one triggers sensitivity):
- `WRITES_DB` on a datastore whose type name matches: `Charge`, `Payment`, `Invoice`, `Credential`, `Session`, `Token`, `Account`, `Order`, `Transaction`
- `CALLS_EXTERNAL` to schema ids matching payment / auth / identity providers
- Atom input or output fields named: `email`, `phone`, `ssn`, `password`, `api_key`, `credit_card`, `address`, `dob`

For each sensitive atom: check if any policy in its module's `policies` list has an `applies_when` that matches. Unguarded → **high** ("sensitive atom with no policy guard").

Proposed fix: route to policy creation (currently manual edit of `L2_policies/<POLICY>.yaml`; future skill will support).

### Step 3 — Compile report

Assemble findings, sort: severity desc (blocking → low), then pass number asc, then location alphabetical.

**Stable IDs:** each finding gets `FND-<hash>` where hash is derived from `<pass>+<location>+<fingerprint>`. Deterministic — same issue across runs gets the same ID.

**Cross-reference with history:**
- For each finding's stable_id: look up in `audit-history.md`
- New (not in history) → `persisted: new`
- Recurring → `persisted: recurring: <N> audits`; escalate severity if run count ≥2
- Previously-resolved → `persisted: regression from <prior_date>`; flag explicitly

**Generate report file** at `<spec-dir>/audit-<YYYY-MM-DD>.md` following the schema in `references/framework.md §10`.

**Chat summary:**
> *"Audit complete. `<N>` findings (`<K>` blocking, `<H>` high, `<M>` medium, `<L>` low). Report at `<path>`.*
> *`<brief top 3 blocking findings as bullets>`*
> *Engage with findings now, or review the report file and come back later?"*

If auto-triggered: add *"Auto-triggered after last atom elicitation completion. No action required right now — when you're ready: `/forge-audit --resume`."*

### Step 4 — Interactive review (conditional on human choice)

If human chooses engage:

Walk findings in severity order — blocking first, always. For each:

1. **Present:**
   - Finding summary + evidence (excerpt from spec, specific lines)
   - Proposed fix (with diff preview if applicable)
   - If historical: escalation note ("this has been flagged 3 runs in a row")

2. **Ask for action:**
   > *"Approve / skip / defer / override-severity?"*

3. **Handle:**
   - **Approve** → apply edit to the spec file (see `## Applying edits` below) + update changelog on affected file + mark finding `resolved` in history
   - **Skip** → leave as `open`; next audit re-flags
   - **Defer** → tag `deferred-<date>`; history tracks duration
   - **Override-severity** → ask new severity; re-tag finding; continue

4. **Move to next finding.**

After all findings processed, summarize:
> *"`<X>` resolved, `<Y>` skipped, `<Z>` deferred, `<W>` severity-overridden."*

**Bulk-approve shortcuts:**
- *"Approve all low severity"* → apply all `low`-severity findings' edits en bloc, summarize outcomes
- *"Approve all auto-fixable"* → same for findings tagged `auto-fixable: true` (metadata attached to some finding types)
- *"Skip all"* → mark everything as `open`, exit review

### Step 5 — Update history + handover

**Update `audit-history.md`:**
- For every finding in this run: upsert entry by stable_id
- Append this run's entry to each finding's `runs` array
- Update `status` based on this run's approval outcome
- Update counts at the top (total, open, resolved, known-risk)

**Handover message:**

If any blocking findings remain `open`:
> *"Implementation should not proceed. `<K>` blocking findings remain unresolved.*
> *- `<FND-001>`: `<description>`*
> *- ...*
> *Resolve these before running `/forge-implement`."*

Else:
> *"Ready for implementation. `<N>` non-blocking findings remain — address when convenient.*
> *Next: `/forge-implement`.*
> *To revisit audit later: `/forge-audit --resume`."*

## Severity escalation

On each finding, before assigning final severity:
1. Start with pass-heuristic proposed severity
2. Look up stable_id in `audit-history.md`
3. If finding appears in ≥2 consecutive prior audits: bump severity one tier (max at blocking)
4. If ≥3 consecutive: force blocking and note: *"this finding has persisted across `<N>` audits. Escalating to blocking."*

Persistence reset: once a finding is `resolved`, its consecutive count resets. A regression starts fresh.

## Applying edits

When human approves an edit:
1. Read the target spec file.
2. Apply the proposed edit (typically an Edit tool call with precise old_string/new_string).
3. Append a changelog entry on the target file:
   ```yaml
   changelog:
     - version:     "<bump>"
       date:        "<YYYY-MM-DD>"
       change_type: fixed
       description: "Audit FND-<id>: <one-line description of the fix>"
   ```
4. Mark finding as `resolved` in the report file and in `audit-history.md`.
5. Record the resolution reference: which finding, which file, which changelog entry.

If the edit fails (e.g., old_string doesn't match because the file changed since the finding was generated): re-read the file, re-derive the edit, present updated diff for re-approval.

## Gotchas

- **Never create new entities.** If a fix requires creating a new atom/type/error/module/policy, the fix text must be a route-back to the creator skill, not a code change. Explicit language: *"Fix: create missing atom via `/forge-decompose PAY` → `/forge-atom atm.pay.<new>`."*
- **Stable IDs matter for escalation.** Compute them deterministically so the same finding surfaces with the same ID every run. Changes to location or fingerprint can produce new IDs — investigate if escalation isn't happening as expected.
- **Auto-triggered audit never blocks.** The only consequence of blocking findings is a warning in handover; forge-implement checks this gate, not forge-audit.
- **History file can get large.** Keep entries even for resolved findings (for regression detection). Archive to `audit-history-archive-<date>.md` when the file crosses ~1000 entries.
- **Regressions are explicit.** When a previously-resolved finding reappears, the finding is tagged `regression from <date>` in the report and highlighted. Regressions frequently indicate the fix was incomplete or a different change reintroduced the issue.
- **Severity overrides persist.** If the human says a finding is a "known acceptable risk," record the rationale and `review-after` date in history. The next audit will still surface it (for awareness) but won't escalate.
- **Scope narrowing excludes whole-project checks.** `--scope <atom>` disables passes 5 (L4 reachability), 7 (policy coverage — project-wide heuristic), because they require cross-module knowledge. Skill announces this at sub-phase 0 exit.
- **Don't trust file paths blindly.** When generating edit diffs, confirm the file hasn't been modified since the audit's pass by re-reading before applying.

## forge CLI commands used

| Command | Used for |
|---|---|
| `forge list --spec-dir <dir>` | Sub-phase 0 baseline counts |
| `forge list --kind <kind> --spec-dir <dir>` | Per-kind iteration during passes (e.g., all atoms for Pass 1) |
| `forge inspect <id> --spec-dir <dir>` | Read a specific entity's metadata during consistency checks |
| `forge context <atom_id> --spec-dir <dir>` | Pass 1 completeness check (exit 2 = unresolved refs) |
| `forge find <query> --kind <kind> --spec-dir <dir>` | Pass 4 hygiene (finding orphans by near-match) + Pass 3g event consumer lookup |

## References

- `references/framework.md` — full mental model:
  - §3 invocation mechanics (manual + auto-trigger)
  - §4 seven audit passes in detail
  - §5 severity model + escalation rules
  - §6 audit-history.md schema
  - §7 sub-phase structure
  - §8 batch review mechanics
  - §10 report + history file schemas
- `assets/audit-report.template.md` — canonical report structure
- `assets/audit-history.template.md` — history file structure
