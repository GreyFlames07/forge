---
name: forge-security
description: Review and improve security coverage across Forge V2 schema artifacts. Use when defining or reviewing `system.security`, `runtime.containers[].security`, `persistent_shapes[].security`, deployment trust boundaries, API/auth flows, sensitive data handling, or security posture for a Forge V2 system or vertical slice. Use after or alongside `forge-schema` and before `forge-build` when the user wants security assumptions made explicit without overbuilding a separate security framework.
---

# forge-security

Read before starting:

- `../../SCHEMA_REFERENCE_V3.md`

## Purpose

Apply security thinking to the Forge V2 schema without turning security into a separate bloated modeling system.

This skill should:

1. Identify the security posture that belongs at `system` level.
2. Identify the security obligations that belong on each relevant runtime container.
3. Identify the security requirements that belong on each relevant persistent shape.
4. Check that deployment trust boundaries match the security story.
5. Route deep, provider-specific, or attack-specific workflows to the external reference skill library.

For a vertical that is about to be implemented, this skill should act as a pre-build gate rather than a post-build cleanup pass.

## Scope Model

Security in Forge V2 is expressed in four places:

1. `system.security`
2. `runtime.containers[].security`
3. `persistent_shapes[].security`
4. `deployment.environments[].nodes[].trust_boundary`

Keep the distinction clean.

### `system.security`

Use for:

- global security posture
- non-negotiable rules
- system-wide authentication assumptions
- data handling rules that apply across the whole system

Do not put container-specific enforcement detail here.

### `runtime.containers[].security`

Use for:

- container-specific authentication or authorization expectations
- secrets handling
- logging restrictions
- access restrictions
- transport/encryption expectations
- service-to-service trust assumptions

Do not restate global policy here unless it changes how the container behaves.

### `persistent_shapes[].security`

Use for:

- encryption at rest expectations
- retention constraints
- masking/redaction rules
- auditability requirements
- sensitivity and access requirements for stored data

Do not create security text for non-persisted payloads here.

### `deployment ... trust_boundary`

Use for:

- where trust assumptions change
- public client environments
- private application networks
- managed data tiers
- third-party boundaries

Do not turn trust boundaries into a full network security model.

## What Good Security Posture Looks Like

In Forge V2, good security posture means the architecture makes the important security assumptions explicit at the right level and turns them into concrete build obligations.

Good security posture usually includes:

1. Clear authentication assumptions
- who can call what
- which flows require identity
- which actions must never be anonymous

2. Clear authorization boundaries
- which containers enforce access control
- which actions are restricted by role, ownership, or capability
- which internal paths are privileged

3. Sensible trust boundaries
- where the system crosses from public to private
- where it talks to third parties
- where sensitive data enters, leaves, or rests

4. Sensitive data handling rules
- what must never be stored
- what must be encrypted at rest or in transit
- what must be masked, redacted, or audited

5. Secrets discipline
- where secrets are used
- which containers handle them
- what must never be logged or exposed

6. Explicit protection of persisted state
- which persisted shapes are sensitive
- what retention, auditability, or access restrictions apply

7. Security language that changes implementation
- the security text should tell builders what must be true
- avoid vague statements like "should be secure"
- prefer specific obligations like "must require authenticated requests" or "must never log payment method tokens"

Signs of weak security posture in the schema:

- security exists only as generic policy language
- trust boundaries are missing
- sensitive persisted shapes have no protection rules
- runtime containers have no clear auth or secrets obligations
- the architecture cannot explain where access control is enforced

## Workflow

### Pass 1: Identify Security-Critical Surfaces

Ask only high-yield questions that cannot be inferred.

Focus on:

- exposed user or system entry points
- mutating flows
- authentication and authorization assumptions
- sensitive stored data
- external integrations

Useful questions:

- What are the most sensitive actions in this system?
- What data would be most damaging if exposed, modified, or deleted?
- Which flows cross trust boundaries or talk to third parties?
- Which containers must enforce access control?

### Pass 2: Draft Security at the Right Level

Draft security content in this order:

1. `system.security`
2. relevant `runtime.containers[].security`
3. relevant `persistent_shapes[].security`
4. `deployment` trust boundaries

Use draft-first mode:

1. draft minimal security text from the existing architecture
2. explain the key logic
3. ask the user to critique the draft
4. revise

### Pass 3: Review for Gaps

Check for:

1. global rules that are missing from `system.security`
2. container-specific controls that are missing from runtime
3. persisted data protections missing from `persistent_shape`
4. trust boundaries that do not match the runtime/deployment story
5. duplicated or vague security text that does not help implementation

## Anti-Bloat Rules

1. Do not create a separate security artifact unless the user explicitly wants one.
2. Keep security where it belongs in the existing schema.
3. Do not restate the same rule at all four levels.
4. Do not add compliance or governance structure unless it changes implementation behavior.
5. Do not create security text for artifacts that do not carry meaningful security obligations.
6. Prefer short, specific security language over broad policy prose.

Use these challenge questions:

- Is this rule global, container-specific, data-specific, or deployment-specific?
- Is this a real implementation obligation or just generic good practice?
- Does this security note change what an engineer or agent would build?
- Is this being repeated unnecessarily at multiple levels?

## Review Rules

### Structural Security Checks

1. `system.security` exists when system-wide security assumptions clearly matter.
2. Runtime containers with meaningful exposure or privileged behavior have `security`.
3. Sensitive `persistent_shape`s have `security`.
4. Trust boundaries exist where public, private, data-tier, or third-party assumptions change.

### Quality Checks

1. Security text is specific enough to guide implementation.
2. Security text is attached to the right artifact level.
3. Security coverage exists for authentication, authorization, secrets, sensitive data, and trust boundaries where relevant.
4. No important sensitive data shape is persisted without explicit protection expectations.

### Consistency Checks

1. API-facing containers and flows agree on auth expectations.
2. Deployment trust boundaries match the runtime and integration story.
3. External integral services are treated consistently across runtime and deployment.
4. Persistent-shape security expectations do not contradict system or container security.

## When to Use External Reference Skills

Use this skill to define the Forge-aligned security model. Do not overload it with deep provider or attack playbooks.

Refer to the external cybersecurity skill library when the task becomes specific to:

- API security testing
- OAuth or token flow design
- cloud IAM auditing
- storage permission auditing
- Kubernetes RBAC review
- Terraform/IaC security review
- TLS hardening
- API gateway or storage access-log analysis
- CI/CD or DevSecOps pipeline security

Useful reference skills include:

- `conducting-api-security-testing`
- `configuring-oauth2-authorization-flow`
- `auditing-aws-s3-bucket-permissions`
- `auditing-gcp-iam-permissions`
- `auditing-azure-active-directory-configuration`
- `auditing-kubernetes-cluster-rbac`
- `auditing-terraform-infrastructure-for-security`
- `configuring-tls-1-3-for-secure-communications`
- `analyzing-api-gateway-access-logs`
- `analyzing-cloud-storage-access-patterns`
- `building-devsecops-pipeline-with-gitlab-ci`

## Routing Rules

- missing or unclear architecture -> `forge-schema`
- general schema consistency review -> `forge-review`
- vertical implementation sequencing or build execution -> `forge-build`
- provider-specific or attack-specific security workflow -> external reference skills

## External Reference Directive

Before relying on the external reference library, always update it first:

```bash
git -C skills/forge-security/anthropic_cybersecurity_skills_reference pull --ff-only
```

After updating, refer to the relevant skills under:

- `skills/forge-security/anthropic_cybersecurity_skills_reference/skills/`

Use the external reference library for specific workflows, but keep the Forge V2 security modeling decisions in this skill.
