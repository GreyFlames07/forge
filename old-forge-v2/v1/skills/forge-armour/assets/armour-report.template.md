# forge-armour report — <scope>

**Generated:** <ISO-8601 timestamp>
**Scope:** <project-wide | module:MOD | atom:atom_id>
**Mode:** <full | advisory>
**Audit baseline:** <supporting-docs/audit-YYYY-MM-DD.md | none>

---

## Security profile summary

- Data sensitivity: <summary>
- Tenancy: <summary>
- Exposure: <summary>
- Auth/authz: <summary>
- Compliance drivers: <summary>
- Top abuse cases: <summary>

---

## Summary

<N> findings total:
- <K_b> blocking
- <K_h> high
- <K_m> medium
- <K_l> low

**Implementation recommendation:** <ready with recommendations | hold implementation pending fixes | advisory only>

---

## Findings

### ARM-<hash8> [BLOCKING] <one-line description>

**Pass:** <N — name>
**Scope:** <project | module:MOD | atom:atom_id | policy:id | operation>
**Risk:** <plain-English risk statement>
**Evidence:** <spec evidence with file / entity references>
**Proposed control:** <recommended control>
**Proposed write set:** <files that would change>
**Approval status:** <pending | approved | skipped | deferred | revised>
**Applied:** <if approved: YYYY-MM-DD at changelog ref>

```diff
--- <file_path>
+++ <file_path>
@@
- <old>
+ <new>
```

---

## Accepted risks

- <finding id> — <rationale> — <review-after date if any>

## Review outcome

- Approved + applied: <count>
- Skipped: <count>
- Deferred: <count>
- Revised: <count>

## Next steps

<If blocking remain: resolve them before /forge-implement.>
<Else: recommended next step is /forge-implement; rerun forge-armour after major trust-model changes.>
