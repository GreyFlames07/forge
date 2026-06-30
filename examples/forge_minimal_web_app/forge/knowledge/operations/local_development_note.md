---
type: note
title: Local Development Notes
refs:
  - container:frontend_ui
  - container:backend_api
  - container:notes_db
tags:
  - development
  - local
status: accepted
updated: 2026-06-30
---

# Local Development Notes

The example app assumes all three runtime containers are available locally:
frontend UI, backend API, and notes database.

## Useful Defaults

- Frontend UI: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Notes database: `localhost:5432`

## Working Agreement

Keep local notes data disposable. Do not encode production secrets or personal
data in fixtures, screenshots, audit output, or example Markdown docs.

