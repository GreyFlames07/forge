---
name: forge-cast
description: >
  Forge V2 casting skill for existing codebases. Use when a user has an implemented project and wants
  to derive a draft Forge V2 schema from the code, config, tests, and contracts that already exist.
  Produces draft V2 schema files plus a cast report that separates high-confidence evidence from open
  uncertainty.
---

# forge-cast

Read before starting:

- `docs/forge-v2-schema.md`
- `docs/forge-v2-architecture.md`
- `frameworks/cast/FRAMEWORK.md`

## Purpose

Translate an existing codebase into a draft Forge V2 schema and workbench context.

This stage should never invent requirements that the repo does not support.

## Evidence Standard

When signals disagree, prefer:

1. executable code and typed schemas
2. config and deployment artifacts
3. tests
4. machine-readable contracts
5. repository docs
6. naming heuristics

Low-confidence conclusions belong in `forge/workbench/cast-report.md`, not as hard schema truth.

## Output Artifacts

| File | Contents |
|------|----------|
| `forge/system.yaml` | Draft system identity and posture |
| `forge/verticals/*.yaml` | Capability slices inferred from repo seams |
| `forge/units/*.yaml` | Runtime boundaries inferred from services, apps, workers, or CLIs |
| `forge/types/*.yaml` | Canonical types inferred from code and contracts |
| `forge/operations/*.yaml` | Business actions inferred from handlers, commands, jobs, or services |
| `forge/surfaces/*.yaml` | Reachability bindings inferred from routes, queues, cron jobs, or commands |
| `forge/stores/*.yaml` | Persistence backbones inferred from config and code |
| `forge/flows/*.yaml` | Higher-confidence end-to-end journeys inferred from orchestration paths |
| `forge/bootstrap.yaml` | Draft first working slice inferred from the most central runnable path |
| `forge/verification/**/*` | Starter checks inferred from health routes, tests, or obvious workflows |
| `forge/workbench/discovery.md` | Repo-level observations and rationale |
| `forge/workbench/cast-report.md` | Uncertain candidates, gaps, and questions for human review |

## Process

### Step 1 — Assess the Repo

Before writing anything:

- identify the runtime profile
- identify runnable entrypoints
- identify exposed interfaces
- identify persistent storage
- identify the likeliest bootstrap path

### Step 2 — Draft High-Confidence Schema

Write only what is strongly supported:

- system
- units
- obvious verticals
- canonical operations
- surfaces
- stores
- bootstrap

### Step 3 — Record Uncertainty

Anything supported only weakly should go to `forge/workbench/cast-report.md` with:

- inferred object
- evidence source
- confidence level
- question for the human

### Step 4 — Hand Over

Recommend the human review:

- the bootstrap draft
- operation boundaries
- auth contexts
- verification gaps

Then route to `forge-spec` and `forge-review`.

## Failure Routing

- If the inferred bootstrap path is weak or contradictory, stop and route to `forge-discover` instead of pretending the repo already implies one clear path.
- If the repo exposes operations or contracts ambiguously, draft only the high-confidence subset and route the rest to `forge-spec`.
- If the human asks for implementation changes during cast, stop and hand off to `forge-build` only after the inferred schema is reviewed.

## Key Constraints

- no speculative requirements
- no implementation changes
- no fake certainty
