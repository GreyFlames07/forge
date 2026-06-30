---
type: test_suite
title: Create Note Contract Tests
refs:
  - flow:create_note
  - entity:note
tags:
  - qa
  - backend
status: accepted
updated: 2026-06-30
---

# Create Note Contract Tests

The create note suite should cover authenticated note creation, rejected
unauthenticated requests, empty title validation, and the response shape used by
the frontend editor.

## Contract Source

Expected behavior comes from the Forge `create_note` container flow and the
operation annotations for the frontend notes screen, backend notes router, note
service, note repository, and note store.

The test suite should treat implementation behavior that contradicts these
contracts as a defect unless the Forge model is explicitly updated.

## Required Scenarios

- Authenticated team member creates a valid note.
- Missing or invalid session token is rejected.
- Empty title is rejected before persistence.
- Empty body is rejected before persistence.
- Successful creation returns a `note_detail_response`.
- Failed creation returns a `note_error_response` that the frontend can render.
- Created notes are persisted as active note records.

## Suggested Test Shape

```python
def test_create_note_requires_authenticated_session(client):
    response = client.post("/notes", json={"title": "Plan", "body": "Draft"})

    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"
```

## Regression Notes

The most important regression risk is accidental divergence between the backend
response shape and the frontend editor state. Keep one test close to the API
contract and one test close to the frontend rendering expectation.

## Out Of Scope

- Rich text note formatting.
- Collaborative editing.
- File attachments.
- Pagination for note lists.
