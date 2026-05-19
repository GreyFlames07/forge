# Forge Plan Framework

## Purpose

Turn schema truth into a minimal, vertical, bootstrap-preserving build plan.

## Core Behavior

- derive slices from bootstrap and flows
- keep the plan machine-readable and human-readable
- prefer the next smallest safe slice
- make verification and operator checks explicit

## Plan Rules

- every slice must reference schema IDs
- every slice must name the units, operations, surfaces, and flows it touches
- every slice must declare the checks that must pass after landing
- every slice must state whether it preserves bootstrap or expands bootstrap

## Files Produced

- `forge/workbench/plan.yaml`
- optionally `forge/workbench/plan.md`

## Effective Planning Order

1. bootstrap slice
2. bootstrap hardening slice
3. adjacent vertical slices that reuse the live bootstrap
4. expansion slices that add non-bootstrap flows

## Exit Condition

There is a clear next slice that an implementation stage can execute without guessing.
