---
name: forge-security
description: Review and improve security posture across the Forge V4 merged model. Use when defining or reviewing system security, container security, entity sensitivity, persistence handling, operation-level access assumptions, trust boundaries, API/auth flows, sensitive data contracts, logging/redaction obligations, or security posture for a Forge V4 build slice. Use after or alongside forge-schema and before forge-build when security assumptions need to become concrete architecture, implementation, or verification obligations.
---

# forge-security

Read before starting:

- `../../FRAMEWORK_V4.md`
- `../../SCHEMA_REFERENCE_V4.md`

Prefer when available:

- `forge crawl --format json`
- `forge context`
- `forge knowledge list`
- `forge audit`

## Purpose

Apply security architecture judgment to the Forge V4 model without creating a
separate security framework.

Security truth should be reviewed across:

```text
central C1/C2 schema
+ code-owned C3 annotations
+ runtime contracts
+ persistence and entity ownership
```

This skill should produce security findings and concrete obligations. It should
not silently redesign the system. Route architecture changes to `forge-schema`,
contract/model correctness issues to `forge-review`, and implementation work to
`forge-build`.

## Knowledge Layer

When available, use `forge knowledge list --ref <kind>:<id>` and filters such
as `--type runbook`, `--type incident`, or `--tag security` to inspect
supporting security notes, incident docs, auth runbooks, compliance notes, and
operational procedures. Treat contradictions with the Forge model as security
or review drift, not as silent truth.

## Decision Log

Read `forge/decisions.yaml` when it exists and use it as security context.

Record or request a decision entry for non-trivial security choices, accepted
risk, trust-boundary placement, authentication or authorization posture,
sensitive-data handling, logging/redaction trade-offs, external dependency
trust, and mitigation deferrals. Use the `forge.decisions` schema from
`SCHEMA_REFERENCE_V4.md`.

Do not let security assumptions live only in chat. If a future reviewer would
need the rationale, make it crawlable.

## Security Principles

Use these principles while reviewing. Name them in findings when useful.

- Least privilege: each actor, container, operation, token, and datastore should
  have only the access required for its job.
- Complete mediation: every sensitive action must have an explicit enforcement
  point; do not rely on upstream UI state or caller honesty.
- Secure by default: unauthenticated, untrusted, or malformed requests should
  fail closed unless a public path is explicitly intended.
- Defense in depth: important protections should not depend on a single control
  when data sensitivity, money movement, account access, or third parties are
  involved.
- Separation of duties: privileged actions, administrative flows, and service
  credentials should be isolated from ordinary user paths.
- Data minimization: collect, pass, persist, and expose only the data required
  for the flow.
- Confidentiality: sensitive data must not leak through logs, responses,
  analytics, browser storage, URLs, error messages, or cross-container contracts.
- Integrity: mutating operations need authorization, validation, idempotency or
  replay resistance where relevant, and clear ownership of state changes.
- Availability and abuse resistance: public or expensive paths should have
  rate-limiting, backpressure, timeout, retry, and degradation assumptions where
  relevant.
- Auditability: high-risk mutations, privileged access, and security-relevant
  failures should produce useful audit events without leaking secrets.
- Explicit trust boundaries: the model should show where trust changes between
  users, clients, servers, data stores, and third parties.
- Principle of least surprise: security behavior should be visible in the model
  where builders and reviewers need it.

## Output Standard

Lead with findings.

Order findings by severity:

1. Public or privileged action lacks authentication or authorization.
2. Sensitive data can leak, be overexposed, or be persisted without protection.
3. Trust boundary or third-party handoff is unclear or unsafe.
4. Mutating contract lacks validation, integrity, idempotency, or auditability.
5. Secrets, tokens, credentials, or session material are mishandled.
6. Availability, abuse resistance, or failure behavior is missing for risky paths.
7. Security text is vague, duplicated, misplaced, or not actionable.

Each finding should include:

- evidence
- violated principle
- impact
- smallest fix direction
- owner skill: `forge-schema`, `forge-review`, or `forge-build`

If no issues are found, say so clearly and note residual risks.

## Workflow

### 1. Load The Merged Model

Start with:

```bash
forge crawl --format json
```

Use crawler output as the source of truth for:

- system security posture
- containers, source roots, deployment entries, and container flows
- entities, lifecycle, ownership, canonical types, and persistence
- extracted components, operations, data shapes, and persistence annotations
- warnings and validation findings

If crawl fails, report that first and route to `forge-review`.

### 2. Focus The Security Scope

Identify whether the security review targets:

- full system
- one business action or runtime flow
- one container
- one entity or persisted data path
- one operation or API surface
- one build slice

Use scoped context only as needed:

```bash
forge context --system --format md
forge context --container <id> --format md
forge context --flow <id> --format md
forge context --entity <id> --format md
forge context --operation <id> --format md
```

### 3. Review Security-Critical Surfaces

Prioritize:

- public entry points
- authentication and session flows
- mutating operations
- privileged/admin operations
- account, money, identity, personal data, or business-critical flows
- persisted sensitive entities
- third-party integrations
- async/retry paths
- logging and observability paths

Ask only questions that cannot be inferred from the model.

### 4. Research Medium-Specific Attack Vectors

When reviewing a real system or codebase with meaningful security exposure,
research current common attack vectors for the system's medium before finalizing
findings. Meaningful exposure includes public input, authentication,
authorization, sensitive data, money movement, third-party calls, privileged
actions, deployment surfaces, or user-controlled persistence/query behavior.

For a small model-only edit outside those areas, do a lightweight trust-boundary
review and state that attack-vector research was not needed.

Use authoritative public references first, such as:

- OWASP Top 10 for web applications
- OWASP API Security Top 10 for API-heavy systems
- OWASP ASVS for web/API control expectations
- cloud, mobile, desktop, or AI security references when the model indicates
  those media

Then identify the five most relevant attack vectors for the system under review.
For a typical web/API application, the candidate set will often include:

- broken access control or broken object-level authorization
- authentication/session/token failures
- injection, including SQL injection and command/template injection
- security misconfiguration and unsafe defaults
- sensitive data exposure through excessive returns, logs, storage, or errors
- SSRF or unsafe consumption of third-party/user-supplied URLs
- mass assignment or broken object property-level authorization
- rate-limit/resource-consumption abuse
- cross-site scripting or browser-side injection for UI-heavy systems
- CSRF for cookie-authenticated browser flows

Select the top five by considering:

- exposed surfaces in the Forge model
- data sensitivity
- trust boundaries
- authentication style
- storage/query technology
- third-party integrations
- browser, API, worker, mobile, CLI, or cloud medium
- code patterns found in the repository

Report the chosen five explicitly before findings when the user asks for a
security review or hardening pass.

### 5. Inspect Code For The Chosen Attacks

After selecting the top five attack vectors, inspect the repository for concrete
evidence that each one is prevented or still possible.

Use targeted searches and code reads. Examples:

- SQL injection: raw SQL construction, string interpolation in queries, unsafe
  ORM escape hatches, unvalidated filter/sort parameters.
- Broken access control/BOLA: handlers or operations that load objects by id
  without owner, tenant, role, or capability checks.
- Authentication failures: weak token validation, missing expiry checks,
  insecure cookie/session settings, password reset token leakage.
- Sensitive data exposure: broad serializers, full entity returns, logs of
  tokens/PII/secrets, stack traces in responses, browser storage of secrets.
- SSRF: user-controlled URLs passed to HTTP clients, metadata/internal network
  access, missing allowlists and scheme/host validation.
- XSS: unescaped HTML rendering, unsafe markdown/HTML injection, dangerous DOM
  sinks, unsanitized rich text.
- CSRF: cookie-authenticated mutations without CSRF or same-site protections.
- Resource abuse: missing rate limits, unbounded pagination, file size gaps,
  expensive queries, retry storms.
- Security misconfiguration: debug modes, permissive CORS, default secrets,
  overly broad allowed hosts, public admin routes.

For each selected attack vector, conclude one of:

- Hardened: code/model shows appropriate controls.
- Partially hardened: controls exist but gaps remain.
- Not hardened: no credible control found.
- Unknown: repository lacks enough evidence; name the missing proof.

When gaps exist, produce implementation obligations for `forge-build` and model
obligations for `forge-schema` or `forge-review`.

## Review Checks

### System Security

Check:

- The global security posture is explicit enough to guide builders.
- Anonymous/public actions are intentionally public.
- Authentication assumptions are clear for protected actions.
- Authorization principles are clear: ownership, role, tenant, capability, or
  policy decision.
- Sensitive data classes and non-negotiable handling rules are named.
- Compliance, retention, data residency, or audit obligations are present when
  they materially affect design.

### Container Security

Check each runtime container for:

- exposure: public client, public API, private service, worker, datastore, or
  third-party boundary.
- enforcement responsibility: which auth, authorization, validation, rate limit,
  and audit checks it owns.
- least privilege: what it can call, read, write, and administer.
- secrets discipline: which credentials it uses and what must never be logged.
- transport expectations: whether traffic requires TLS, service identity, mTLS,
  signed requests, or private networking.
- failure behavior: timeouts, retries, backpressure, and safe degradation where
  relevant.

### Flow And Contract Security

For each runtime flow and each operation participating in it, check:

- The trigger has a clear trust level.
- Every mutating step has an authorization story.
- Every input crossing a trust boundary is validated before use.
- Sensitive fields are not passed farther than needed.
- Outputs and returns do not expose internal, secret, or excessive data.
- Branch conditions do not depend on untrusted data without validation.
- Error paths fail closed and do not reveal sensitive implementation detail.
- Retryable or payment/order/account flows have idempotency or replay-resistance
  assumptions where relevant.
- Audit events exist for high-risk decisions, state changes, and denied access.

Route pure contract continuity issues to `forge-review`, but keep security
findings here when the contract creates access, leakage, integrity, or abuse risk.

### Entity And Persistence Security

Check each entity and persistence annotation for:

- sensitivity classification: public, internal, personal, confidential,
  regulated, credential, financial, or security event.
- logical owner and persisted location are clear.
- encryption, retention, deletion, masking, and access rules are explicit when
  needed.
- canonical types and operation returns do not overexpose persisted fields.
- lifecycle transitions that change access or sensitivity are protected.
- durable audit trail exists for high-value state changes.

### C3 Annotation Security

Check extracted annotations for:

- interface components identify actor, surface, input/output, and security where
  meaningful.
- operations express auth-sensitive inputs and returns accurately.
- persistence annotations do not hide sensitive storage behavior.
- data shapes identify sensitive fields through names, descriptions, security
  notes, or surrounding entity rules.
- local/component flows do not bypass central container security assumptions.

### Audit And Observability Security

Check:

- Logs and audit events are useful for investigation.
- Logs do not include tokens, passwords, secrets, payment credentials, session
  cookies, raw PII, or excessive payloads.
- Security failures are observable without exposing internals to callers.
- Monitoring expectations exist for abuse-prone flows.

## Drafting Security Text

When asked to add or refine security text, keep it short and actionable.

Good examples:

- "Requires authenticated requests; authorization is enforced by account owner
  membership before any note data is returned."
- "Must never log access tokens, refresh tokens, password reset tokens, session
  cookies, or raw authorization headers."
- "Persists email address and note content; encrypt at rest, redact from logs,
  and delete on account erasure."

Avoid:

- "Use best practices."
- "Make this secure."
- "Validate inputs" without saying which container or operation owns validation.

## External Reference Use

Use this skill for Forge-aligned security modeling. When the request becomes
provider-specific, attack-specific, or tool-specific, research current primary
or authoritative sources for the relevant attack patterns, hardening guidance,
and verification techniques before inspecting the codebase.

Examples:

- OAuth flow design
- cloud IAM audit
- Kubernetes RBAC review
- Terraform/IaC security review
- API security testing
- TLS hardening
- CI/CD security

If a local reference library is available in the source checkout, treat it as
optional background only. Do not assume it exists in installed packages or
initialized projects, and do not let it replace current research.

## Routing

Route fixes to:

- `forge-schema` for missing security posture, boundaries, entities, containers,
  or flow ownership.
- `forge-review` for broken references, malformed annotations, or non-security
  contract continuity problems.
- `forge-build` for implementation, tests, C3 annotations, logging, validation,
  authorization checks, or runtime controls.
- external security references for provider/tool/attack-specific workflows.

## Guardrails

- Do not create security bloat that does not change architecture,
  implementation, or verification.
- Do not restate the same control everywhere; place it at the level where it is
  enforced or relied on.
- Do not hide uncertainty behind generic security language.
- Do not assume the UI enforces server-side authorization.
- Do not treat TLS as a substitute for authorization.
- Prefer specific obligations over policy prose.
