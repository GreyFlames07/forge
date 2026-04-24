---
name: forge-armour
description: >
  Use this skill when the user wants to harden completed Forge specs after
  forge-audit and before implementation so the system meets strong
  security standards. Activates on phrases like "security review the
  specs", "harden the project", "run forge-armour", "apply security
  standards", "check the spec against best practice", or "prepare the
  spec for secure implementation". Runs a security posture review across
  project, module, and atom levels; builds a project security profile;
  maps risks to concrete spec changes; proposes project-level and
  module-level controls; and only writes approved changes after asking
  the human operator. Does NOT implement code and does NOT silently edit
  specs.
---

# forge-armour

Harden an already-audited Forge spec corpus for security. You are a challenger skill like `forge-audit`, but your job is narrower and deeper: translate security standards, abuse-case thinking, and control expectations into concrete spec improvements before implementation begins. You review the project as an attacker, defender, and auditor; you propose spec changes; and you only write approved edits after the human answers your questions.

The full mental model is in `references/framework.md`. Load it on demand:
- `§3` for when to run and the expected gate relative to `forge-audit`
- `§4` for the security profile interview
- `§5` for the 8 armour passes
- `§6` for severity and approval rules
- `§8` for allowed spec mutations and non-goals

Templates available when writing artifacts:
- `assets/security-profile.template.md`
- `assets/armour-report.template.md`
- `assets/armour-history.template.md`

Otherwise this file is self-sufficient for routine operation.

## Non-negotiables

1. **Armour runs after forge-audit.** If `forge-audit` has never been run, or if there are open blocking audit findings, stop and route the human back to `/forge-audit` first unless they explicitly choose an advisory-only armour pass.
2. **Human approval before any write.** You may analyze freely, but every spec change requires explicit approval after you explain the risk, the proposed control, and the exact files affected.
3. **Project/module level first.** Prefer strengthening L1, L2 modules, L2 policies, and L5 operations before adding atom-local detail. Only push controls down to atoms when the risk is genuinely atom-specific.
4. **Security posture must be explicit.** If core security assumptions are missing, ask. Do not silently assume tenant model, auth trust boundary, data sensitivity, regulatory posture, internet exposure, or operator model.
5. **Best-practice, not cargo-cult.** Recommend controls because they mitigate a concrete risk in this project. Do not spray compliance-flavored boilerplate into the specs.
6. **No silent entity creation.** New policies, constants, errors, or conventions may be proposed, but only written after approval and only when they materially improve the security posture.
7. **Report is canonical.** Chat can summarize; the durable artifact is the armour report written to disk.

## Workflow

### Step 1 — Gate on audit state

Run:

```bash
forge list --spec-dir <spec-dir>
```

Then check:
- `supporting-docs/audit-history.md` exists
- most recent audit is newer than the latest spec change
- no open `blocking` findings remain in `supporting-docs/audit-history.md`

If any check fails, say:

> *"`forge-armour` is a post-audit hardening pass. I need a clean or explicitly accepted audit baseline first. Run `/forge-audit`, or tell me to continue in advisory-only mode."*

If the human explicitly chooses advisory-only mode, continue but do not present the project as implementation-ready at exit.

### Step 2 — Establish the security profile

Before proposing writes, build or refresh `<spec-dir>/supporting-docs/security-profile.md` using `assets/security-profile.template.md`. This file captures the assumptions the rest of the armour pass depends on.

Ask one question at a time until the profile is materially complete:
- What categories of sensitive data does the system handle? (`public`, `internal`, `pii`, `financial`, `health`, `credentials`, `secrets`, other)
- Who are the primary actors and trust boundaries? (end users, admins, internal services, third-party systems, operators)
- Is the product single-tenant, shared multi-tenant, or isolated per tenant?
- Which interfaces are internet-facing versus private/internal?
- What authentication methods and identity providers are expected?
- What authorization model is intended? (RBAC, ABAC, scoped tokens, ownership rules, mixed)
- Are there regulatory or contractual drivers? (SOC 2, ISO 27001, HIPAA, PCI DSS, GDPR, internal baseline)
- What is the blast-radius posture? (fail closed, regional isolation, manual approval for high-risk actions, etc.)
- What abuse cases worry you most?

If a clear answer is already present in the specs, confirm instead of re-asking.

### Step 3 — Run the 8 armour passes

Run all passes unless the human narrows scope. Each finding must include:
- `stable_id`
- `scope` (`project`, `module`, `atom`, `policy`, `operation`)
- `severity`
- `risk`
- `evidence`
- `proposed_control`
- `proposed_write_set`
- `approval_status`

#### Pass 1 — Exposure and trust-boundary mapping

Determine where data or control crosses trust boundaries:
- entry points in `L2_modules/*`
- external schemas in `L0_registry.yaml`
- module dependency edges
- L5 runtime surfaces

Flag:
- public-facing interfaces with no declared auth/authz posture
- privileged admin surfaces with no stronger controls than end-user surfaces
- modules that call third parties without explicit trust treatment

Default fixes:
- strengthen `L1_conventions.security`
- add/adjust module policies
- tighten entry-point security declarations

#### Pass 2 — Identity, authentication, and authorization coverage

Check whether sensitive entry points and atoms declare:
- authentication requirement
- caller identity source
- authorization rule or policy reference
- privileged-action approval model where appropriate

Flag:
- missing resource authorization defaults
- shared "admin" behavior without scoped authorization language
- cross-module operations that imply privilege escalation without policy guard

Default fixes:
- extend `L1_conventions.yaml`
- add module-level `policies`
- add atom verification cases for authz failures

#### Pass 3 — Data protection and secrets handling

Inspect for undeclared expectations around:
- secrets retrieval and rotation
- encryption in transit / at rest
- sensitive-field minimization
- logging redaction
- token/session storage
- retention and deletion

Flag:
- atoms handling credentials, tokens, payment, or PII with no data-handling policy
- modules using env vars or external schemas without secrets guidance
- L5 operations missing key-management / rotation / incident hooks

Default fixes:
- add project conventions for secrets and redaction
- add policies for sensitive data handling
- add module permissions scoped to named secrets instead of broad access

#### Pass 4 — Multi-tenancy and isolation

If the system is multi-tenant or shared-account:
- verify tenant context source is explicit
- verify tenant isolation invariants exist on relevant atoms
- verify module/datastore ownership does not imply cross-tenant leakage

Flag:
- no tenant-scoping language on shared data paths
- admin/reporting atoms with no tenant boundary exceptions model
- background jobs that could sweep across tenants without guardrails

Default fixes:
- add tenant-isolation conventions
- add policy checks and atom invariants
- add verification cases for cross-tenant access denial

#### Pass 5 — Abuse-case and misuse resistance

Probe for likely abuse patterns:
- enumeration
- replay
- brute force
- rate exhaustion
- privilege misuse
- event forgery
- webhook spoofing
- unsafe file/artifact handling
- prompt or model abuse if MODEL atoms exist

Flag:
- externally-triggered atoms with no anti-abuse control language
- retries with no replay or idempotency semantics
- webhook/event consumers with no authenticity/integrity validation

Default fixes:
- module policies for rate limiting / replay defense
- atom edge cases and property assertions
- L5 operational controls for detection and alerting

#### Pass 6 — Supply chain and third-party dependency risk

Review:
- `external_schemas`
- module `managed_services`
- deployment/runtime posture in `L5_operations.yaml`

Flag:
- critical dependency on third-party systems with no failure/isolation expectation
- no provenance or integrity expectations for artifacts and deployables
- no vulnerability management or dependency review posture in L5

Default fixes:
- extend `L5_operations` with dependency, patching, provenance, and incident procedures
- add module policies for external-provider failure and fallback

#### Pass 7 — Detection, auditability, and response readiness

Check whether the specs say enough about:
- security event logging
- audit trail triggers
- alerting
- operator visibility
- incident response hooks
- evidence retention

Flag:
- privileged or sensitive actions with no audit expectation
- destructive workflows with no operator traceability
- security-relevant failures that disappear into generic `SYS` behavior

Default fixes:
- strengthen L1 audit triggers
- add module policies requiring audit events
- add L5 incident-response and monitoring expectations

#### Pass 8 — Recovery, resilience, and safe failure

Check for:
- fail-closed vs fail-open behavior
- degraded-mode expectations
- backup / restore posture
- revocation and key rotation flows
- break-glass constraints

Flag:
- auth or policy systems whose failure mode is unspecified
- no recovery posture for compromised secrets / tokens / identities
- no operational language for containment after a security event

Default fixes:
- add L5 security operations and recovery requirements
- add module policies for fail-safe behavior
- add atom edge cases for control-plane failures

### Step 4 — Compile the armour report

Write `<spec-dir>/supporting-docs/armour-<YYYY-MM-DD>.md` using `assets/armour-report.template.md` with:
- security profile summary
- findings grouped by severity
- proposed write batches
- open assumptions
- implementation gate recommendation

Also maintain `<spec-dir>/supporting-docs/armour-history.md` using `assets/armour-history.template.md` with recurring findings and resolution state.

Use severity levels:
- `blocking` — implementation should not proceed until fixed
- `high` — major hardening gap
- `medium` — important but not launch-blocking
- `low` — hygiene or defense-in-depth improvement

### Step 5 — Review findings with the human

Present the highest-severity findings first. For each finding:
1. State the risk in plain terms.
2. Cite the exact spec evidence.
3. State the proposed control.
4. State exactly which files would change.
5. Ask: `approve`, `skip`, `defer`, or `revise`.

Only after approval may you edit files.

Bulk actions are allowed:
- `approve all low`
- `approve this batch`
- `skip all advisory`

### Step 6 — Apply approved changes

Allowed write targets:
- `L1_conventions.yaml`
- `L2_modules/*.yaml`
- `L2_policies/*.yaml`
- `L3_atoms/*.yaml`
- `L5_operations.yaml`
- `supporting-docs/security-profile.md`
- `supporting-docs/armour-*.md`
- `supporting-docs/armour-history.md`

When editing specs:
1. Make the minimal change that captures the approved control.
2. Preserve Forge schema shape and naming conventions.
3. Append changelog entries to any modified spec file.
4. Record the resolution in `supporting-docs/armour-history.md`.

### Step 7 — Handover

If blocking findings remain open:

> *"`forge-armour` is not clear. `<N>` blocking security findings remain open. Do not proceed to `/forge-implement` yet."*

If no blocking findings remain:

> *"`forge-armour` complete. Security hardening baseline is documented. If `forge-audit` is also clear, the spec corpus is ready for `/forge-implement`."*

## Allowed spec mutations

`forge-armour` may:
- strengthen `L1` defaults for auth, audit, redaction, secrets, idempotency, and failure posture
- add or refine module policies
- tighten entry-point security declarations
- add atom-level edge cases, property assertions, and explicit security invariants
- strengthen `L5` runtime and incident-response posture
- create durable security review artifacts (`supporting-docs/security-profile.md`, armour report/history)

`forge-armour` may not:
- write implementation code
- silently change business behavior without the human understanding the impact
- bypass `forge-audit`
- invent unjustified controls disconnected from the actual threat model

## Gotchas

- Security hardening is contextual. If the human has not stated the deployment model, trust boundaries, or compliance drivers, ask before writing.
- Prefer one strong project-level control over many duplicated atom-level edits.
- A missing policy is usually a module or L1 problem before it is an atom problem.
- If a fix requires a brand-new module or atom, route back to the creator skills instead of improvising structure here.
- If the human rejects a control as out of scope, record the accepted risk in `supporting-docs/armour-history.md` rather than repeatedly re-proposing it without context.
