# Forge Spec Framework

## Purpose

Define the canonical system truth needed before implementation drift begins.

This stage owns:

- types
- operations
- surfaces
- stores
- flows
- verification

## Core Behavior

- interview in focused batches
- define critical operations explicitly
- define contracts canonically
- define only as much detail as needed to build the next slices safely

## Interview Standard

Questions should prioritize:

- canonical operations
- payload and error contracts
- runtime reachability
- persistence semantics
- flow-critical behavior
- bootstrap-relevant verification

Avoid:

- asking about every possible edge case before the first runnable slice exists
- over-modeling future flows when the next vertical slice is still unclear

## Files Produced

- `forge/types/*.yaml`
- `forge/operations/*.yaml`
- `forge/surfaces/*.yaml`
- `forge/stores/*.yaml`
- `forge/flows/*.yaml`
- `forge/verification/**/*`

## Effective Question Order

1. What operations must exist for the bootstrap slice?
2. What reaches those operations?
3. What goes in, what comes out, what can fail?
4. What canonical data must exist?
5. What stores are required?
6. What end-to-end flows matter first?
7. What checks prove bootstrap and critical flows still work?

## Exit Condition

The bootstrap slice and next vertical slice are spec-complete enough to plan and build.
