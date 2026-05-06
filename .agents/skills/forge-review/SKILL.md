---
name: forge-review
description: >
  Forge spec review skill. Use when spec work is complete (or a module is ready for review)
  and the user wants to validate quality, consistency, and security before implementation.
  Combines completeness audit, consistency checking, contract verification, and domain-specific
  attack vector analysis into a single pass. Opens by asking the human for their security posture
  and intent. Produces workbench/review.md with a severity-ranked findings report and proposed
  spec edits that the human approves individually.
  Triggers on: "review the spec", "audit this", "forge-review", requests to check quality or
  security of a Forge spec before implementation begins.
---

# forge-review

Read `references/framework.md` before starting. Also read `workbench/discovery.md` for system context.

## Purpose

Stress-test the spec for gaps, contradictions, and security weaknesses **before implementation begins**. This is a challenger skill — it reads and proposes edits, never creates new nodes. If a finding requires a new entity, the proposed fix routes back to `forge-spec`.

## Security Posture Interview (required first step)

Before running any passes, ask the human:

1. **Threat model**: Who are you worried about? (external attackers, insider threats, compromised services, none yet)
2. **Data sensitivity**: What's the most sensitive data this system handles? Any PII, financial, health, or regulated data?
3. **Compliance**: Any compliance requirements? (SOC 2, GDPR, HIPAA, PCI, etc.)
4. **Auth posture**: Is the default "deny unless authenticated" or is there public access? What roles exist?
5. **Entry points**: What surfaces are exposed? (public HTTP API, internal gRPC, event consumers, CLI, websockets)

Record answers in `workbench/review.md` under `## Security Posture`. These answers drive which attack vectors are relevant and calibrate severity.

---

## Review Passes

Run all six passes. Collect all findings before presenting.

### Pass 1 — Completeness

- All elements have at least one operation.
- All operations have `inputs`, `outputs`, and `raises` declared (even if empty lists).
- All `contract` references on operations point to an existing contract file.
- All `external_dependencies` on modules have a corresponding integration file.
- `implementation/datastores.yaml` exists if any module declares datastore consumers.
- `implementation/environments.yaml` exists and has an entry for each environment type.

Run `forge validate` — all structural errors are automatic P1 findings.

### Pass 2 — Consistency

- Every type referenced anywhere exists in `types/` or is a built-in scalar.
- Every error referenced anywhere exists in `errors/` or is a built-in error.
- Every policy referenced on a node exists in `policies/`.
- Every `caller` and `callee` in interactions references a real operation ID.
- Every `interaction` referenced in flow steps exists.
- Every `producer` and `consumer` in contracts references a real module.
- Module `elements` lists match element files on disk.

Use `forge find` to spot type/error duplication (same concept, different names).

### Pass 3 — Contract Correctness

For each contract:
- `inputs` and `outputs` are fully defined composites, not bare primitives.
- `protocol` matches how the contract is consumed.
- Every consuming module lists this contract in `external_dependencies`.
- Versioning strategy is declared.

For each operation with a `contract`: verify `inputs`/`outputs` match.

### Pass 4 — Access Control and Auth

Using the stated posture as the benchmark:
- Every `command` and `async_command` operation has a security policy — inherited or direct.
- Every public-facing operation (`visibility: public`) has explicit auth declared. Flag any with `authentication: required: false` unless the human confirmed it intentional.
- Auth mechanisms on actors match what's declared in policies.
- Role-based access rules are present on any operation that mutates state or accesses sensitive data.
- `rate_limit` policies exist on public-facing contracts.
- Sensitive fields (passwords, tokens, secrets, PII) carry `classification: restricted` or `confidential` data policies.
- Datastores holding sensitive data have a policy with `encryption: at_rest: true`.

### Pass 5 — Attack Vector Analysis

This pass is **domain-specific**. Use the security posture interview answers and the system's exposure surface (entry points, protocols, data types) to determine which vectors are relevant. Do not apply every vector mechanically — apply the ones that fit this system's actual threat surface.

#### Master attack vector list

Check each applicable vector against the spec. For each hit, propose a concrete spec fix (new policy, new error, constraint on a type, or a note in the operation's raises list).

**Injection**
- **SQL injection**: Any operation that takes user-supplied strings and passes them to a datastore — does the spec declare parameterised query enforcement or an ORM policy? Flag raw string concatenation patterns in operation descriptions.
- **NoSQL injection**: Same check for document/key-value datastores — does the spec constrain query input types?
- **Command injection**: Any operation that shells out or executes system commands — are inputs constrained to a strict type with an allowlist pattern?
- **LDAP / XPath injection**: Relevant if the system integrates with directory services or XML data sources.
- **Template injection**: Any operation that renders user-supplied content into templates (email, PDF, HTML reports).

**Cross-Site Scripting (XSS)**
- Any operation that accepts free-text user input and whose output is rendered in a browser context — does the spec declare output encoding / sanitisation as a policy or type constraint?
- Stored XSS: does the spec declare sanitisation at write time for user content stored in datastores?
- Reflected XSS: do query/search operations constrain input types to prevent script reflection?

**Cross-Site Request Forgery (CSRF)**
- Any state-mutating operation exposed via a REST or websocket contract — does the spec declare a CSRF token policy or require `SameSite` cookie semantics?

**Broken Authentication / Session Management**
- Token operations (issue, refresh, revoke) — are all three paths declared with appropriate errors (`Unauthorized`, `Forbidden`)?
- Session expiry — is it declared as a constraint on a token type or as a policy?
- Password / credential operations — does the spec declare hashing policy (not storage of plaintext)?

**Insecure Direct Object Reference (IDOR)**
- Any operation that takes a user-supplied ID and returns or mutates a resource — does the spec declare ownership/authorisation checks in the operation's policy or raises list?

**Security Misconfiguration**
- Default credentials or secrets — are any default values set on sensitive fields in type definitions?
- Debug/admin endpoints — are any operations marked `visibility: internal` that are exposed via a public contract?
- Error messages — do error types expose internal stack traces or system details in their `fields`?

**Sensitive Data Exposure**
- PII or financial data in error `fields` — flag any error that echoes back user-supplied sensitive input.
- Logging of sensitive fields — if operational policies declare `log_entry: true` on operations handling credentials or PII, flag it.
- Unencrypted data in transit — any integration without `encryption: in_transit: true` in an applied policy.

**Broken Access Control**
- Privilege escalation: any operation that changes a user's role or permissions — does it require elevated auth?
- Horizontal escalation: multi-tenant systems — does the spec declare tenant isolation as a type constraint or policy rule?
- Missing function-level access control: internal operations (`visibility: internal`) exposed through public contracts.

**XML / Deserialization**
- Any operation that accepts XML, JSON with arbitrary keys, or binary serialisation formats — are input types constrained to prevent entity expansion or deserialization gadget attacks?

**Server-Side Request Forgery (SSRF)**
- Any operation that accepts a URL or endpoint as input and makes an outbound request — does the spec declare an allowlist constraint on the URL type?

**Mass Assignment**
- Any operation that maps a request body wholesale onto an entity — does the input type explicitly declare only the permitted fields (no catch-all)?

**Rate Limiting and Denial of Service**
- Any public operation without a `rate_limit` policy — flag for review.
- Operations that trigger expensive computation or external calls — does the spec declare timeouts or circuit-breaker policies?

**Business Logic**
- Workflow bypass: can flow steps be invoked out of order via direct operation calls? Does the spec declare sequencing invariants?
- Negative values / boundary violations: do numeric input types declare `min`/`max` constraints for financial or quantity fields?
- Replay attacks: do idempotency policies exist on payment or state-mutation operations?

#### How to apply

For each applicable vector:
1. Identify which elements, operations, or types are exposed to it.
2. Check whether the spec already mitigates it (type constraint, policy, error in `raises`).
3. If not mitigated: rate severity, write the finding, propose the specific spec edit.

Skip vectors with zero exposure in this system — note them as `N/A [reason]` in the report.

### Pass 6 — Data Governance

- Every datastore has `consistency` and `durability` declared.
- Every datastore handling personal or sensitive data has a data policy with `retention` declared.
- Audit policies (`AuditTrigger`) exist on operations that touch classified data.
- Environment entries use secrets references (e.g. `${{ secrets.X }}`), not plain text credentials.

---

## Output Format

Write `workbench/review.md`:

```markdown
# Spec Review — <date>

## Security Posture
[Summary from interview]

## Attack Vectors Assessed
[List of vectors checked, with N/A and reason for skipped ones]

## Findings

### P1 — Critical (blocks implementation)
- **[PASS] [node-id]**: [finding]. **Proposed fix**: [edit or route-to-skill].

### P2 — High
...

### P3 — Medium
...

### P4 — Advisory
...

## Proposed Spec Edits
[Before/after YAML snippets for each approved edit]
```

**Severity calibration:**
- P1: Broken references, forge validate errors, unprotected mutations on sensitive data, exploitable injection surface with no mitigation declared
- P2: Missing auth on exposed operations, IDOR with no ownership check, missing CSRF on state-mutating REST contracts, unencrypted sensitive datastore
- P3: Missing rate limits, incomplete error coverage, data policy gaps, missing idempotency on financial operations
- P4: Advisory improvements, type constraint tightening, naming, optional fields

---

## Approval Flow

1. Present findings summary grouped by severity.
2. For each proposed edit: show before/after YAML, ask for approval.
3. Apply approved edits immediately. Mark declined as `[DECLINED]`.
4. Run `forge validate` after all edits to confirm clean.

## Key Constraints

- Never create new nodes. Route to `forge-spec` if new entities are needed.
- Severity is proposed, not enforced — human may override any rating.
- Do not apply edits without explicit human approval.
- Attack vector pass is domain-specific — do not flag vectors with no exposure in this system.
- `workbench/review.md` is overwritten on each run.
