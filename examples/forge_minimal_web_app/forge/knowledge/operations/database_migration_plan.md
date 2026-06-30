---
type: migration
title: Notes Database Migration Plan
refs:
  - container:notes_db
  - entity:note
  - entity:session
tags:
  - database
  - migration
status: draft
updated: 2026-06-30
---

# Notes Database Migration Plan

Use this plan when changing the database shape for users, sessions, or notes.
The Forge entity model remains the source of truth for ownership and lifecycle.

## Plan

1. Compare the proposed table change with `forge/entities.yaml`.
2. Add or update migration tests for affected record shapes.
3. Apply the migration to a disposable local database.
4. Run account and note smoke checks.
5. Record any architecture-relevant trade-off in `forge/decisions.yaml`.

## Rollback

For local development, rebuild the disposable database from fixtures. For a
production-style environment, require a backward migration or a restore point
before applying destructive changes.

