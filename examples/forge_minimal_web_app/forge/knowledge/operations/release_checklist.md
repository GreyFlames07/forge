---
type: checklist
title: Team Notes Release Checklist
refs:
  - flow:create_note
  - flow:list_notes
  - flow:archive_note
tags:
  - release
  - qa
status: draft
updated: 2026-06-30
---

# Team Notes Release Checklist

Use this checklist before promoting a Team Notes build beyond local
development.

## Checks

- Account registration succeeds for a new visitor.
- Sign-in rejects invalid credentials.
- Authenticated note creation returns a note detail response.
- Active notes are listed in update order.
- Archived notes disappear from the active list.
- Session material is not printed in browser or backend logs.

## Exit Criteria

The release is ready when the account and note workflows pass, no validation
findings are unexplained, and the Forge audit matches the intended runtime
model.

