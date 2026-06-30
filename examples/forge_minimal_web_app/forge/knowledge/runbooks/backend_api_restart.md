---
type: runbook
title: Backend API Restart
refs:
  - container:backend_api
tags:
  - operations
  - development
status: accepted
updated: 2026-06-30
---

# Backend API Restart

Restart the backend API after confirming no local migrations or test runs are in
progress. Re-run the account and notes smoke checks after the process is back.

## When To Use

Use this runbook when the local backend API is unresponsive, returning stale
responses after a code change, or needs to be restarted after dependency or
environment updates.

Do not use this runbook to recover from database migration failures. In that
case, pause and inspect the database state before restarting services.

## Preconditions

- Confirm no one is running an active demo against the local backend.
- Check that pending database migrations are either complete or intentionally
  deferred.
- Save any local changes that affect API startup configuration.
- Keep the frontend running so the post-restart smoke check can verify the full
  browser-to-API path.

## Restart Steps

1. Stop the current backend process.
2. Confirm the old process released the API port.
3. Start the backend API with the project’s normal development command.
4. Watch the startup logs for import errors, missing environment variables, and
   failed database connections.
5. Run the smoke checks below.

```bash
curl http://localhost:8000/health
curl http://localhost:8000/notes
```

## Smoke Checks

- Register a temporary user.
- Sign in as that user.
- Create a note with a title and body.
- Refresh the notes list and confirm the note appears.
- Archive the note and confirm it no longer appears in the active list.

## Escalation

If startup succeeds but note creation fails, inspect the `create_note` flow in
the Forge audit before changing code. If startup fails before the API binds to
the port, inspect configuration and dependency errors first.
