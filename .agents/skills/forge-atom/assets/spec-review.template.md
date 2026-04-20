# Spec review presentation template (draft-first)

Use this structure when presenting the drafted spec to the human for review.
The goal is a readable, decision-friendly layout that makes corrections,
assumptions, and unresolved choices easy to surface.

---

## Standard layout

```
Here's the drafted spec. Review — what's wrong or missing?

## assumptions made

  - <assumption 1>
  - <assumption 2>

## decision points

  - <question where multiple valid choices exist>
  - <input/output contract question only if ambiguity or risk remains>

## spec

  input:  <type_id or inline fields>
  output:
    success: <type_id or inline fields>
    errors:  [<codes>]
  side_effects: [<markers>]

  invariants:
    pre:  [<pre-conditions>]
    post: [<post-conditions>]

  logic:
    <normalized DSL lines — grouped by case if helpful for review>

  failure_modes:
    <trigger → error mapping>

## verification (from draft + review)

  property_assertions:  [<N>]
  example_cases:        [<M>]   — examples surfaced while reviewing the draft
  edge_cases:           [<K>]   — edge paths or failure paths surfaced during review

## L0 changes pending

  types:     <new types + auto-write tier>
  errors:    <new errors pending confirmation>
  constants: <new constants + single-consumer flags>

## Module cascades pending

  persistence_schema.datastores:  <additions>
  access_permissions:             <additions>
  interface.entry_points:         <stub completions>

## Consistency flags (if any surfaced)

  <named constraint> — <resolution recorded>

---
What's wrong?
```

## Review patterns

When the human says:

- **"Change output.errors to include X"** → check X exists in L0; if not, run error reuse probe first; then update output, check logic has a RETURN X path, check failure_modes has a trigger for X.
- **"The logic is wrong at step N"** → replay the case that generated that step; update the logic; re-check invariants and failure_modes for consistency.
- **"Add a case"** → ask the human to walk the new case; integrate into logic; add to example_cases or edge_cases as appropriate.
- **"The draft assumed the wrong input/output contract"** → revise the contract, then re-check logic, invariants, failure_modes, and caller expectations that depend on it.
- **"Remove field X from input"** → scan logic for references to `input.X`; remove or refactor each; check invariants.pre and example_cases for references to the field.
- **"This isn't in the right module"** → STOP elicitation. Return atom to stub state, update its `owner_module`, remove from current module's `owned_atoms`, add to new module's `owned_atoms`. Re-run elicitation in the new module's context (different sibling patterns, different policies, different conventions).

## What NOT to do during review

- Don't ask the human to produce DSL corrections. They say "add a step that validates the amount"; you update the DSL.
- Don't silently accept corrections that violate invariants you just established. If the correction contradicts an invariant, probe: *"Adding this step would violate invariant `<pre/post X>`. Revise the invariant, or find a different way to handle this?"*
- Don't re-run the full consistency probe sweep after every minor correction. Only re-check what the correction could affect (e.g., if logic changes, re-check probes 2, 3, 6; if side_effects change, re-check 1, 4, 5).
- Don't add verification items that aren't grounded in the review. If a property assertion can't be derived from the draft, the caller context, or what the human clarified, ask: *"Where does this invariant come from?"*
