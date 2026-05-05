# forge-audit history

Persistent record of every finding ever surfaced across audit runs. Used by `forge-audit` to detect recurring findings, escalate persistent ones, and flag regressions.

**Last updated:** <ISO-8601 timestamp>
**Total findings ever surfaced:** <N>
**Open:** <count>  **Resolved:** <count>  **Known-risk:** <count>  **Regressed:** <count>
**Latest contract root:** <path | absent>
**Latest contract hash:** <hash | absent>

---

## Findings

<entries ordered by stable_id>

### FND-<hash8> — <one-line description>

**Stable ID fingerprint:** `<pass>+<location>+<content_hash>`
**First flagged:** <YYYY-MM-DD>
**Last flagged:** <YYYY-MM-DD>
**Status:** open | resolved | known-risk | regressed
**Runs:** <count>
**Severity history:**
- <YYYY-MM-DD>: low
- <YYYY-MM-DD>: medium (escalated — 2 consecutive)
- <YYYY-MM-DD>: high (escalated — 3 consecutive)

**Resolution** (if status=resolved):
- Resolved on: <YYYY-MM-DD>
- Resolved by: approved edit in supporting-docs/audit-<date>.md
- Commit/changelog ref: <file:changelog version>
- Fix description: <what was done>

**Known-risk rationale** (if status=known-risk):
- Accepted on: <YYYY-MM-DD>
- Rationale: <why the risk is acceptable>
- Review-after: <YYYY-MM-DD — when to re-evaluate>

**Regression note** (if status=regressed):
- Regressed on: <YYYY-MM-DD>
- Previously resolved on: <YYYY-MM-DD>
- Likely cause: <if known — e.g., "spec edit reverted the earlier fix">

**Report references:**
- supporting-docs/audit-<YYYY-MM-DD-1>.md (first flagged)
- supporting-docs/audit-<YYYY-MM-DD-2>.md
- supporting-docs/audit-<YYYY-MM-DD-3>.md

---

### FND-<hash8> — <description>

(same structure)

---

<... every finding ever surfaced ...>

---

## Archive policy

When this file exceeds ~1000 entries, archive older resolved findings to `supporting-docs/audit-history-archive-<YYYY-MM-DD>.md` and keep only open / known-risk / recently-resolved entries here. The archive stays searchable but stops loading on every audit run.
