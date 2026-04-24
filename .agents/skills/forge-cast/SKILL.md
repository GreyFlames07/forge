---
name: forge-cast
description: >
  Use this skill when the user wants to translate an existing non-Forge
  codebase into a draft Forge spec corpus. Activates on phrases like "hydrate
  this repo into Forge", "document the existing project in Forge", "reverse
  engineer specs from code", "cast this codebase", or "turn this repo into
  Forge docs". Creates or updates the Forge schema files from repository
  evidence only: project foundation docs, L0 vocabulary candidates, L2 module
  files, L3 atoms/artifacts, and any L4 flows/journeys that are explicit in
  the code or config. Produces a separate uncertainty report with evidence,
  confidence levels, and optional clarification questions. Does NOT invent
  business intent, hidden requirements, or unstated behaviors.
---

# forge-cast

Translate an existing software project into a draft Forge corpus using only evidence visible in the repository. `forge-cast` is a hydration skill, not a speculation skill. It extracts the best supportable Forge shape from code, config, tests, docs, migrations, API contracts, and deployment files, then makes uncertainty explicit instead of filling gaps with plausible fiction.

The full mental model is in `references/framework.md`. Load it on demand:
- `§2` when deciding what counts as admissible evidence
- `§3` when mapping repo structure into L0-L5 outputs
- `§4` when deciding whether a flow/journey is explicit enough to write
- `§5` when assembling the uncertainty report and clarification questions

This file is self-sufficient for routine operation.

## Non-negotiables

1. **Evidence only.** Every spec statement must be traceable to code, config, tests, docs, migrations, or repository metadata.
2. **No hidden-intent invention.** If the repo does not reveal business meaning, leave it unresolved and record the gap.
3. **Draft the corpus anyway.** Missing certainty is not a reason to stop; write the parts that are supportable and mark the rest.
4. **Foundation before behavior.** Recover project structure and vocabulary first, then atoms, then orchestration.
5. **Prefer explicit interfaces over internal heuristics.** Endpoints, jobs, events, schemas, migrations, public methods, and tests outrank inferred call-graph guesses.
6. **Confidence is mandatory.** Every major output area must be reflected in the uncertainty report with confidence and evidence.
7. **Questions are optional and targeted.** Ask only for ambiguities that materially improve the corpus; do not run a broad discovery interview.
8. **Do not overwrite authored Forge intent blindly.** If a Forge corpus already exists, update it as a hydration pass and preserve human-authored decisions unless contradicted by current code and explicitly called out.

## Workflow

### Step 1 - Detect repo + Forge state

Run the minimum discovery commands needed to establish state:

```bash
forge list --spec-dir <spec-dir>
rg --files <repo-root>
```

If no Forge spec dir exists yet, create the standard structure first:

```bash
forge init --skip-skills
```

Use the repo root as truth and the Forge spec dir as output. If a Forge corpus already exists, treat it as prior authored context and reconcile carefully.

### Step 2 - Gather admissible evidence

Read only the files needed to map the codebase:

1. top-level manifests: package files, lockfiles, build configs
2. runtime/deploy configs: Docker, CI, infra, env examples
3. entrypoint surfaces: routes, controllers, CLI commands, workers, event consumers
4. schemas and storage evidence: migrations, ORM models, protobuf/OpenAPI/GraphQL specs
5. tests that reveal intended behavior
6. existing docs that describe concrete system behavior

Prefer direct evidence over summaries. If docs and code disagree, record the contradiction and bias toward executable reality unless the user says otherwise.

### Step 3 - Hydrate the Forge corpus

Write or update:

- `supporting-docs/discovery-notes.md`
- `L0_registry.yaml`
- `L1_conventions.yaml` only where defaults are explicit from code/config/tooling
- `L2_modules/*.yaml`
- `L3_atoms/*.yaml`
- `L3_artifacts/*.yaml` where non-executing dependencies are explicit
- `L4_flows/*.yaml` and `L4_journeys/*.yaml` only when the orchestration is explicit enough to support them
- `L5_operations.yaml` only from visible deployment/runtime evidence

Hydration order:

1. project shape and boundaries
2. shared vocabulary
3. modules and ownership seams
4. atoms/artifacts
5. orchestration
6. operational posture

### Step 4 - Write the uncertainty report

Always produce:

- `<spec-dir>/supporting-docs/cast-report.md`

For each major area, include:

1. what was written
2. source evidence
3. confidence (`high`, `medium`, `low`)
4. unresolved ambiguities
5. optional clarification questions only where answers would materially improve the corpus

Question style:

- targeted
- evidence-backed
- specific file/entity references
- no generic brainstorming prompts

### Step 5 - Handover

At handover, state one of:

- hydration draft complete; next step `/forge-audit`
- hydration draft complete but human clarification recommended for listed areas
- hydration blocked because the repo lacks enough executable/config evidence for a safe draft

## Writing rules by layer

### L0

- Create domain types/errors/constants only when they are explicit in schemas, models, enums, validators, contracts, or repeated business vocabulary.
- Do not elevate one-off local DTO names into shared project vocabulary unless reuse is evident.

### L1

- Capture only explicit defaults: retry policies, logging patterns, auth posture, validation floors, idempotency standards, error envelopes.
- If conventions are inconsistent across modules, record that inconsistency rather than forcing a fake global default.

### L2

- Prefer repo/package/service boundaries already present in the codebase.
- If the codebase is monolithic, create modules only where the ownership seam is visible from directory structure, interface boundaries, or dependency direction.

### L3

- Atoms should map to smallest meaningful executable responsibilities visible in the code.
- Use handlers, commands, jobs, consumers, route actions, service methods, or workflow steps as seeds.

### L4

- Only write flows/journeys when sequencing is explicit in code, workflow engines, route-state machines, saga orchestrators, or well-supported integration tests.
- If orchestration is only implicit across scattered calls, leave it in `supporting-docs/cast-report.md` as a candidate rather than writing fiction.

### L5

- Pull from deployment manifests, queue config, cron schedules, infra code, metrics, alerts, CI/CD, and env configuration.
- Do not manufacture SLOs, rate limits, or release strategies without evidence.

## What forge-cast does NOT do

| Not done | Why |
|---|---|
| Invent missing product intent | Hydration must remain evidence-bound |
| Replace human-authored architecture decisions silently | Existing Forge docs may intentionally differ from code |
| Guarantee correctness of inferred semantics | The uncertainty report is part of the deliverable |
| Implement code changes | This is a documentation/specification pass only |
