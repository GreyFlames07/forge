# Decomposition candidates — `<MOD>`

Running list produced by `forge-decompose` during sub-phase 1 (multi-pass extraction). Appended to `discovery-notes.md` under the module's section. Each candidate carries the pass that surfaced it so gaps in a given pass are easy to spot.

## Candidate atoms

```yaml
candidate_atoms_for_<MOD>:
  # Pass 1 — Primary golden path
  - name:        <placeholder label>
    source:      pass_1
    description: <one-line summary>
    status:      pending_review

  # Pass 2 — Alternate use cases
  - name:        <placeholder label>
    source:      pass_2
    description: <one-line summary>
    status:      pending_review

  # Pass 3 — Error paths and compensations
  - name:        <placeholder label>
    source:      pass_3
    description: <one-line summary>
    status:      pending_review

  # Pass 4a — Data lifecycle audit
  - name:        <placeholder label>
    source:      pass_4a
    description: <one-line summary>
    status:      pending_review

  # Pass 4b — Side-effect coverage audit
  # Pass 4c — Interface coverage audit
  # Pass 4d — Cross-module inbound audit
  # Pass 4e — Maintenance / background audit
  # (add entries under each as surfaced)
```

## Storage-neutral entity hints

Captured during the walkthroughs — not committed to `L2_modules` until `forge-atom` runs.

```yaml
likely_persisted_entities_for_<MOD>:
  - entity_concept: <logical name>
    written_by:     <atom_id>
    read_by:        [<atom_ids>]
    likely_keys:    [<field names>]
    # storage form (relational | document | key_value | ...) decided at forge-atom
```

## Open questions

Unresolved cross-module references, ownership ambiguity, kind disambiguation deferred, or any other thing the session couldn't close.

```yaml
open_questions:
  - summary:     <short description>
    kind:        unresolved_cross_module_call | ownership_ambiguity | kind_deferred | other
    blocking:    <true | false>
    recommended: <next step>
```

## Status lifecycle (for each candidate)

- `pending_review`    — surfaced by a pass; not yet reviewed by the human
- `pending_classification` — review complete; kind/ownership probes pending
- `stubbed`           — classified and written to `L3_atoms/`
- `dropped`           — explicitly removed during review (rationale in a comment)
- `moved_to_<MOD>`    — ownership moved to another module
