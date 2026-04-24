# forge-cast — Framework

This is the human-facing mental model for `forge-cast`: the hydration skill
that translates an existing non-Forge codebase into a draft Forge corpus while
staying anchored to repository evidence.

## 1. Purpose and position in the pipeline

`forge-cast` brings legacy or pre-existing projects into Forge:

```
existing repo -> cast -> audit -> armour -> implement/validate
```

Outputs can include:

- `supporting-docs/discovery-notes.md`
- `L0_registry.yaml`
- `L1_conventions.yaml`
- `L2_modules/*.yaml`
- `L3_atoms/*.yaml`
- `L3_artifacts/*.yaml`
- `L4_flows/*.yaml`
- `L4_journeys/*.yaml`
- `L5_operations.yaml`
- `supporting-docs/cast-report.md`

Non-goals:

- no speculative business requirements
- no implementation changes
- no forced completion of layers unsupported by evidence

## 2. Admissible evidence hierarchy

Use this order when signals disagree:

1. Executable code paths and type/schema definitions
2. Config and deployment artifacts
3. Tests with explicit assertions
4. Machine-readable contracts (OpenAPI, GraphQL, protobuf, async specs)
5. Repository docs with concrete behavior statements
6. Naming heuristics and structural patterns

The lower the evidence class, the more likely the output belongs in
`supporting-docs/cast-report.md` as a candidate rather than a written spec fact.

## 3. Hydration strategy by layer

### Foundation

Create the Forge project skeleton first if missing. Hydration should not depend
on a human running the rest of the pipeline beforehand.

### L0

Recover shared vocabulary from:

- schemas
- models
- validators
- enums
- response envelopes
- repeated domain nouns across modules

Do not promote transport-only or single-call DTOs unless reuse is visible.

### L1

Recover conventions only when the repo shows stable defaults:

- shared middleware
- framework base classes
- common retry wrappers
- global logging/error handlers
- auth middleware
- CI/test standards

If conventions vary by module, document inconsistency rather than forcing a
single project default.

### L2

Map modules from:

- packages/services/apps in a monorepo
- top-level bounded directories
- separate deployables
- clear dependency-direction seams inside a monolith

### L3

Map atoms from smallest meaningful executable responsibilities:

- route handlers
- command handlers
- workers
- consumers
- service entry methods
- scheduled tasks

### L4

Only hydrate L4 when sequencing is explicit:

- workflow engine definitions
- saga coordinators
- queue pipelines
- controller/service orchestration with strong test support
- frontend state-machine journeys

### L5

Recover runtime and operations from visible evidence:

- deployment manifests
- infrastructure-as-code
- queue/cron config
- CI/CD
- metrics/alert rules
- environment docs/examples

## 4. Explicitness threshold for L4

Write an L4 artifact only if all are true:

1. Start condition is identifiable
2. Step order is visible
3. Invoked units are resolvable enough to name
4. Success/failure exits are at least partially visible

If only 1-2 are true, keep it as an L4 candidate in `supporting-docs/cast-report.md`.

## 5. The uncertainty report

`supporting-docs/cast-report.md` is mandatory, not a fallback.

Recommended sections:

1. Scope scanned
2. Corpus written
3. Evidence summary by layer
4. Confidence table
5. Contradictions found
6. Clarification questions
7. Suggested next skill

Confidence levels:

- `high`: explicit code/config/contracts
- `medium`: multiple aligned signals, some naming/structural interpolation
- `low`: partial signals only; human review strongly recommended

## 6. Handover routing

- Hydrated corpus looks coherent: run `/forge-audit`
- Security-sensitive codebase: run `/forge-armour` after audit
- Large unresolved intent gaps: ask targeted clarification questions, then rerun `forge-cast` or continue with manual cleanup
