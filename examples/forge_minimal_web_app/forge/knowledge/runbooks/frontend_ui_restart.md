---
type: runbook
title: Frontend UI Restart
refs:
  - container:frontend_ui
tags:
  - operations
  - development
status: accepted
updated: 2026-06-30
---

# Frontend UI Restart

Restart the local frontend UI when browser refreshes keep showing stale assets
or when Vite dependency metadata needs to be rebuilt.

## Preconditions

- Confirm the backend API is still running.
- Save any frontend changes that should survive the restart.
- Keep the browser tab open so the post-restart refresh path can be checked.

## Restart Steps

1. Stop the current frontend development server.
2. Clear local dependency cache only when dependency resolution is failing.
3. Start the frontend with the normal development command.
4. Refresh the Team Notes browser tab.

## Smoke Checks

- Sign in with a known local user.
- Create a note from the editor.
- Refresh the note list and confirm the new note still renders.

