---
type: review
title: Session Token Handling Notes
refs:
  - entity:session
  - container:frontend_ui
  - container:backend_api
tags:
  - security
  - auth
status: draft
updated: 2026-06-30
---

# Session Token Handling Notes

Session tokens should stay out of logs, URLs, and rendered error messages. The
frontend and backend should treat session material as sensitive even in local
development fixtures.

## Security Intent

Session tokens prove an authenticated session and should be handled as bearer
secrets. Any component that receives a token must minimize where it stores,
prints, forwards, or persists that value.

## Handling Rules

- Do not include session tokens in URLs.
- Do not log request headers that contain session material.
- Do not return raw session tokens in user-facing error messages.
- Do not store tokens in long-lived browser state unless the product explicitly
  chooses that persistence model.
- Redact token values in diagnostics, test snapshots, and audit output.

## Review Checklist

Before shipping a sign-in or note mutation change, check:

- The frontend submits tokens only to the backend API.
- The backend authenticates the token before mutating notes.
- Invalid tokens fail closed.
- Session lookup paths do not leak whether a token once existed.
- Test fixtures use obviously fake token values.

## Example Redaction

```text
session_token: sess_1234567890abcdef
session_token: sess_1234...[redacted]
```

## Follow-Up Questions

The example app does not yet make a final decision about cookie-based sessions
versus explicit bearer tokens. That decision should be recorded before a real
production implementation.
