# Forge Knowledge Layer

Forge keeps architecture truth in central YAML and code-owned annotations. The
knowledge layer is for supporting Markdown docs that should travel with that
model without becoming canonical architecture.

Use `forge/knowledge/**/*.md` for runbooks, test suites, deployment notes,
security notes, incident guides, migration plans, domain glossaries, and other
delivery knowledge.

Knowledge docs use small YAML frontmatter:

```md
---
type: runbook
title: Restart Backend API
refs:
  - container:backend_api
tags:
  - production
status: accepted
updated: 2026-06-30
---

# Restart Backend API

Steps go here.
```

Required fields:

- `type`: one of `runbook`, `test_suite`, `checklist`, `guide`, `note`,
  `glossary`, `incident`, `migration`, or `review`
- `title`: human-readable name

Optional fields:

- `refs`: Forge refs such as `container:backend_api`, `flow:create_note`,
  `entity:note`, `component:note_service`, `operation:create_note`,
  `data_shape:note_record`, or `decision:use_postgres`
- `tags`: free-form labels
- `status`: `draft`, `accepted`, or `stale`
- `updated`: `YYYY-MM-DD`

Knowledge docs support the model. They do not define it. If a doc contradicts
the structured Forge model, treat that as drift to review.

Useful commands:

```bash
forge knowledge --ref container:backend_api
forge knowledge --type runbook
forge knowledge --tag production
forge context --container backend_api --format md
```
