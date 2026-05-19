# Forge Cast Framework

## Purpose

Hydrate a Forge V2 schema from an existing implementation without inventing unsupported behavior.

## Core Behavior

- evidence first
- no speculative requirements
- prefer executable code over docs when they disagree
- write only what the codebase supports
- surface uncertainty in workbench artifacts

## Evidence Hierarchy

1. executable code paths and type/schema definitions
2. config and deployment artifacts
3. tests with explicit assertions
4. machine-readable contracts
5. repository docs with concrete behavior
6. naming heuristics

## Outputs

- draft files under `forge/`
- `forge/workbench/discovery.md`
- `forge/workbench/cast-report.md`

## Exit Condition

The repo has a defensible draft schema plus an explicit uncertainty report.
