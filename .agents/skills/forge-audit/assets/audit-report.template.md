# forge-audit report — <scope> — <tier>

**Generated:** <ISO-8601 timestamp>
**Scope:** <project-wide | module:MOD | atom:atom_id>
**Tier:** <quick | full>
**Atoms scanned:** <N>
**Passes run:** <list, e.g., 1,2,3,4,5 for quick tier>

---

## Summary

<K> findings total:
- <K_b> blocking
- <K_h> high
- <K_m> medium
- <K_l> low

**State:** <"Ready for implementation" | "Blocking findings present — hold implementation" | "<K_b> blocking findings must be resolved before implementation">

**Regressions:** <count of findings that reappeared after prior resolution>
**Escalations:** <count of findings escalated due to persistence>
**Contract artifact:** <absent | stale | generated at <spec-dir>/contract/<lang>>

---

## Findings

<findings sorted: severity desc, then pass asc, then location alphabetical>

### FND-<hash8> [BLOCKING] <one-line description>

**Pass:** <N — name>
**Location:** <file:line | entity_id>
**Persisted:** <new | recurring: N audits | regression from YYYY-MM-DD | escalated from <prior_severity>>

**Evidence:**

```
<excerpt or reference showing the issue>
```

**Proposed fix:**

<description of the fix. If fix requires new entity creation, state explicitly:
"Requires creation — route to /forge-decompose or /forge-atom">

<optional diff preview:>
```diff
--- <file_path>
+++ <file_path>
@@ line <N> @@
- <old content>
+ <new content>
```

**Approval status:** <pending | approved | skipped | deferred | overridden-to-<severity>>
**Applied:** <if approved: YYYY-MM-DD at commit/changelog ref>

---

### FND-<hash8> [HIGH] <description>

(same structure)

---

<... all findings ...>

---

## Review outcome (populated after interactive review)

- **Approved + applied:** <count>
- **Skipped:** <count>
- **Deferred:** <count>
- **Severity-overridden:** <count>
- **Resolved in this run (regressions or fresh):** <count>

## Next steps

<if blocking remain: "Resolve the N blocking findings before proceeding to /forge-implement.">
<else: "Ready for /forge-implement. Non-blocking findings can be addressed at your discretion.">
