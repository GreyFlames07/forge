---
name: forge-validate
description: >
  Forge V2 validation skill. Use when the user wants to validate that the current implementation still
  matches schema truth. Runs through schema validation, startup and bootstrap checks, surface and flow
  checks, and operator-gated verification where needed. Produces forge/workbench/validation.md and
  updates forge/workbench/status.yaml.
---

# forge-validate

Read before starting:

- `docs/forge-v2-schema.md`
- `docs/forge-v2-architecture.md`
- `frameworks/validate/FRAMEWORK.md`
- current files under `forge/`
- `forge/workbench/plan.yaml` if present

## Purpose

Validate that the current system still satisfies declared truth, especially:

- startup
- bootstrap
- critical surfaces
- critical flows
- operator-confirmed checkpoints

This is a skill-stage, not a public CLI command. It writes validation state back into `forge/workbench/` as an internal framework artifact.

## Non-negotiables

1. Read-only with respect to implementation and schema.
2. Bootstrap is validated before broader flow coverage.
3. Do not mark something verified without tying it to a declared verification item.
4. Operator checks are real checks, not a fallback excuse.
5. Always write the validation artifact, even on partial runs.

## Validation Phases

### Phase 1 — Schema and Reference Validation

Check:

- references resolve
- required bootstrap objects exist
- verification files are coherent
- plan and status artifacts do not reference nonexistent schema IDs

### Phase 2 — Startup

Validate declared startup items:

- healthcheck commands
- service reachability
- boot readiness

If the system is already running, use that state. Do not start it twice.

### Phase 3 — Bootstrap

Validate the bootstrap slice before anything else:

- required units are up
- required surfaces behave as expected
- required stores are available at the needed level for the slice
- success criteria actually hold

If bootstrap fails, say so clearly and stop treating the system as generally healthy.

### Phase 4 — Surfaces and Flows

Validate:

- declared surface behavior
- declared flow behavior
- critical errors and side effects where they matter

Focus first on the bootstrap vertical, then adjacent critical flows.

### Phase 5 — Operator Verification

Where schema declares operator verification items:

- present the exact check to the human
- capture whether it was confirmed, declined, or not run
- record it in the validation artifact and status artifact

## Output

Write:

- `forge/workbench/validation.md`
- `forge/workbench/status.yaml`

The report should state:

- what passed
- what failed
- what was skipped
- what still needs operator confirmation
- whether bootstrap is healthy

## Failure Routing

- If schema references are broken, route back to `forge-spec` before treating runtime results as meaningful.
- If bootstrap fails, stop broader validation and hand the issue back to `forge-build`.
- If a validation check cannot be tied to a declared verification item, stop and route the gap back to `forge-spec`.
- If only operator confirmation is missing, do not call the system verified; hand off explicitly to the human operator or `forge-build` for follow-up.

## Key Constraints

- Never blur bootstrap verification with broader validation.
- Never claim flow-level health if bootstrap is broken.
- Never omit operator-gated checks from the report.
