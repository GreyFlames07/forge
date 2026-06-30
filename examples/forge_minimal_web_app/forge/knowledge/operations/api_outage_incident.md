---
type: incident
title: Backend API Local Outage
refs:
  - container:backend_api
  - flow:create_note
tags:
  - incident
  - operations
status: draft
updated: 2026-06-30
---

# Backend API Local Outage

Use this incident note when the frontend is reachable but note actions fail
because the backend API is unavailable or returning repeated server errors.

## Triage

- Confirm `http://localhost:8000/health` responds.
- Check whether the backend process is still bound to port `8000`.
- Inspect the latest startup logs for import, database, or environment errors.
- Confirm the notes database is reachable from the backend process.

## Recovery

Restart the backend API only after checking whether a migration, test run, or
debug session owns the failure. If the API returns to health, rerun create,
list, and archive note smoke checks.

