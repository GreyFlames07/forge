---
name: forge-cast
description: >
  Forge casting skill for existing codebases. Use when a user has an existing project (code,
  config, docs) and wants to bring it into the Forge spec system. Reads the repository using
  an evidence hierarchy (code > config > tests > contracts > docs > naming heuristics) and produces
  a draft Forge spec corpus anchored to what the repository actually does — no speculative
  requirements, no invented structure.
  Triggers on: "cast this repo", "reverse engineer this codebase into forge", "forge-cast",
  or any request to derive a Forge spec from an existing project.
---

# forge-cast

Read `references/framework.md` before starting — you need the full schema for all output files.

## Purpose

Translate an existing codebase into a draft Forge spec corpus. Every spec claim must be anchored to repository evidence. The output is a starting point — not a complete spec. Ambiguous or uncertain areas go into `workbench/cast-report.md` as candidates for human review.

## Evidence Hierarchy

When signals disagree, use this precedence:

1. **Executable code paths and type/schema definitions** — highest confidence
2. **Config and deployment artifacts** (docker-compose, k8s manifests, terraform, CI)
3. **Tests with explicit assertions**
4. **Machine-readable contracts** (OpenAPI, GraphQL schema, protobuf, AsyncAPI)
5. **Repository docs with concrete behavior statements**
6. **Naming heuristics and structural patterns** — lowest confidence; goes to cast-report, not spec files

The lower the evidence class, the more likely the output belongs in `workbench/cast-report.md` rather than a committed spec file.

## Output Artifacts

| File | Contents |
|------|----------|
| `spec/conception.yaml` | Conception, actors (from auth/middleware code), glossary |
| `spec/<system>/system.yaml` | System node inferred from repo structure |
| `spec/<system>/<domain>/domain.yaml` | Domains inferred from package/module boundaries |
| `spec/<system>/<domain>/<module>/module.yaml` | One per service/package with packaging + runtime |
| `spec/<system>/<domain>/<module>/<element>.yaml` | Elements with inline properties + operations |
| `spec/<system>/types/<TypeName>.yaml` | Types extracted from schema definitions |
| `spec/<system>/errors/<ErrorName>.yaml` | Errors extracted from error enums, HTTP status handling |
| `spec/<system>/policies/<policy>.yaml` | Policies inferred from auth middleware, rate limiters, validators |
| `spec/<system>/contracts/<contract>.yaml` | Contracts from OpenAPI / protobuf / explicit interface boundaries |
| `spec/<system>/interactions/<interaction>.yaml` | Interactions from service-to-service call sites |
| `spec/<system>/flows/<flow>.yaml` | Flows from orchestration code or explicit workflow definitions |
| `spec/<system>/implementation/datastores.yaml` | Datastores from ORM schemas, migrations, connection config |
| `spec/<system>/implementation/environments.yaml` | Environments from CI/CD config, .env files, deployment manifests |
| `spec/<system>/workbench/discovery.md` | System overview, decisions inferred, open questions |
| `spec/<system>/workbench/cast-report.md` | Uncertain candidates, low-confidence inferences, gaps |

## Hydration Strategy by Node Type

### Conception and Actors

- Scan auth middleware and JWT/OAuth config for actor types.
- Scan route guards, RBAC definitions, and permission checks for roles.
- Infer `auth_mechanism` from auth library usage (e.g. `passport-jwt` → `jwt`).
- Glossary: extract domain terms from README, API docs, or prominent naming patterns.

### System and Domains

- Infer system name from repo name, package name, or root README.
- Identify domains from top-level package structure, monorepo workspace names, or service directories.
- `platform`: infer from `Dockerfile`, CI provider, cloud SDK imports.
- `language`: infer from file extensions and package managers.
- `deployment`: infer from infra config (lambda → `cloud`, k8s → `cloud`, docker-compose alone → `on_prem`).

### Modules

- One module per deployable service, microservice, or bounded package.
- `packaging.kind`: infer from entry point type (HTTP server → `service`, cron → `job`, Lambda handler → `function`).
- `packaging.runtime`: read from `Dockerfile`, `.nvmrc`, `pyproject.toml`, `go.mod`.
- `packaging.scaling`: infer from HPA config, auto-scaling groups, Lambda concurrency settings.
- `external_dependencies`: scan import statements and HTTP client call sites.

### Elements

- Map classes/structs to elements. Use `kind` heuristics:
  - Has identity field + lifecycle methods → `aggregate` or `entity`
  - No identity, immutable → `value_object`
  - No state, only behavior → `service`
  - Read-only derived state → `projection`
- Properties: extract from class fields, ORM column definitions, schema types.
- Operations: extract from public methods, route handlers, exported functions.

### Types and Errors

- Extract composite types from DTOs, request/response bodies, ORM models, protobuf messages.
- Extract scalar types from validated fields with explicit constraints (regex, min/max).
- Extract errors from error enums, HTTP status mappings, custom exception classes.
- Do not extract types that are purely internal implementation detail with no cross-module exposure.

### Contracts

- Create contracts from OpenAPI paths, protobuf service definitions, GraphQL schema types, or explicit interface files.
- Where no machine-readable contract exists but clear service-to-service HTTP calls do, infer a contract from the call site — note as evidence class 1, but flag in cast-report for human confirmation.

### Datastores

- Extract from ORM entity definitions, migration files, connection strings in config.
- `engine`: read from driver package name (e.g. `pg` → `postgres`, `mongoose` → `mongodb`).
- `kind`: map engine to StorageType enum.
- `schemas`: map ORM entities/collections to `storage_name` (table/collection name).

### Environments

- Extract from `.env.example`, CI/CD pipeline variables, deployment manifests.
- `region`: from cloud config (e.g. `AWS_REGION`, GCP `--region` flags).
- `instance_class`: from RDS/CloudSQL instance type config, if present.

## Uncertainty Handling

When confidence is below evidence class 3 (tests):
- Write the candidate to `workbench/cast-report.md` under `## Uncertain Candidates`.
- Do not write it to a spec file.
- Format: `- [<evidence class>] <node-type> <proposed-id>: <inferred value> — <reason for uncertainty>`

When a section has no evidence at all, note it as a gap in `cast-report.md` under `## Spec Gaps`.

## Completion

After writing all files:
1. Run `forge validate` — resolve structural errors (broken ID references, missing required fields).
2. Summarise what was produced, what evidence class each major decision used, and what's in the cast-report.
3. Recommend the human reviews `workbench/cast-report.md` and then runs `forge-spec` to fill gaps, followed by `forge-review`.

## Key Constraints

- No speculative requirements — only what the repo evidences.
- No implementation changes — spec only.
- Do not force-complete sections unsupported by evidence; leave them as gaps.
- `status: draft` on all generated nodes.
- All `id` fields must match path-derived IDs — run `forge validate` to confirm.
