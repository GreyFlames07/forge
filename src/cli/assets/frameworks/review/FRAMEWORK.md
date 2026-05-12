# Forge Review Framework

## Purpose

Review schema and implementation for drift, bugs, weak contracts, security issues, and missing verification.

## Review Priorities

1. bootstrap fragility
2. contract drift
3. invariant violations
4. security posture gaps
5. missing or weak verification
6. structural complexity that does not earn its cost

## Core Behavior

- findings first
- prefer concrete references to schema objects and code paths
- distinguish schema weaknesses from implementation weaknesses
- identify whether a finding blocks build, review, or promotion

## Outputs

- `forge/workbench/review.md`
- concrete remediation recommendations

## Exit Condition

The user has a prioritized set of findings or an explicit clean review with residual risks.
