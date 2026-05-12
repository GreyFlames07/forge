# Forge Validate Framework

## Purpose

Prove that the current system still satisfies schema truth, especially bootstrap and critical flows.

## Core Behavior

- validate schema references
- validate startup
- validate bootstrap
- validate declared surfaces
- validate declared flows
- require operator confirmation where machine checks are insufficient

## Validation Priorities

1. does it boot
2. does bootstrap still work
3. do critical surfaces behave as declared
4. do critical flows behave as declared
5. what remains unverified or operator-gated

## Outputs

- `forge/workbench/validation.md`
- `forge/workbench/status.yaml`

## Exit Condition

There is a clear statement of what passed, what failed, and what still needs human confirmation.
