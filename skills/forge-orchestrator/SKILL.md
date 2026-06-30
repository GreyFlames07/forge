---
name: forge-orchestrator
description: Use when coordinating Forge V4 work across business discovery, schema design, hydration, review, security, build, audit, scoped context, or knowledge-layer docs.
---

# forge-orchestrator

## Purpose

Coordinate Forge work and route to the smallest specialist skill that fits.

Forge has two context layers:

```text
structured model = canonical architecture truth
forge/knowledge/**/*.md = supporting runbooks, tests, security notes, operations notes, glossaries, and guides
```

Knowledge docs can support decisions, reviews, and builds. They do not define
canonical architecture. If knowledge contradicts the Forge model, report drift.

## Skills

- `forge-business`: product, market, MVP, users, business actions
- `forge-schema`: C1/C2 system design, containers, flows, entities, decisions
- `forge-hydrate`: reverse-engineer existing code into Forge schema/annotations
- `forge-review`: quality gate, drift, broken refs, over-modeling
- `forge-security`: trust boundaries, sensitive data, auth, abuse paths
- `forge-build`: thin slice implementation, C3 annotations, QA tests

## Commands

Prefer the narrowest useful command:

```bash
forge init
forge crawl --format json
forge context --system --format md
forge context --container <id> --format md
forge context --flow <id> --format md
forge context --entity <id> --format md
forge context --component <id> --format md
forge context --operation <id> --format md
forge context --data-shape <id> --format md
forge knowledge list
forge knowledge list --ref <kind>:<id>
forge knowledge list --type <type>
forge knowledge list --tag <tag>
forge audit
```

If a command is unavailable, inspect the matching files directly.

## Routing

1. Classify the request.
2. Run `forge crawl --format json` when a Forge workspace exists.
3. Pull scoped context with `forge context`.
4. Pull supporting knowledge with `forge knowledge list --ref <kind>:<id>` when a target id is known.
5. Route to the specialist skill.

Common sequences:

```text
business -> schema -> review/security -> build -> review
hydrate -> review -> schema/security/build
security -> schema/build/review
```

Do not broaden scope just because multiple skills exist.

## Output

For coordination work, report:

- selected skill path
- commands used
- structured context target
- knowledge docs used
- next concrete action
- unresolved drift or ambiguity
