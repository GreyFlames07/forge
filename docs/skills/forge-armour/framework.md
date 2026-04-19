# forge-armour — Framework

This document is the source-of-truth mental model for `forge-armour`. It defines how the skill should behave, when it should run, what it may change, and how it should convert security posture thinking into concrete Forge-spec mutations.

It is not the compact `SKILL.md`; it exists so the skill can stay short while still having a clear operating model.

---

## 1. What forge-armour is

**Purpose.** `forge-armour` is a post-audit hardening gate that runs after `forge-audit` and before `forge-implement`. Its job is to ensure the spec corpus expresses a credible security posture at the project, module, and atom levels.

Where `forge-audit` asks:
- Is the spec complete?
- Is it internally consistent?
- Will it likely work?

`forge-armour` asks:
- Does the spec express an explicit trust model?
- Are sensitive paths governed by strong enough controls?
- Do project and module policies reflect high-standard security practice?
- Would an implementer know how to build the system safely without making up security decisions?

This is a challenger skill, not a creator skill and not an implementation skill.

---

## 2. Role contrast

| Skill | Primary role | Main question |
|---|---|---|
| `forge-discover` | interviewer | what system are we building? |
| `forge-decompose` | extractor | what atoms belong here? |
| `forge-atom` | contract author | what exactly does this atom do? |
| `forge-audit` | quality challenger | what is incorrect, inconsistent, or missing? |
| `forge-armour` | security challenger | what security assumptions, controls, and hardening requirements are missing or too weak? |

`forge-armour` is complementary to `forge-audit`, not a replacement. Audit validates structural correctness. Armour validates security posture sufficiency.

---

## 3. When it runs

Preferred invocation points:
- After a clean `forge-audit`
- After major spec changes that materially affect trust boundaries, auth, tenancy, or sensitive data handling
- Before a first `/forge-implement` run
- Before external review, customer security review, or compliance preparation

Invocation forms:
- `/forge-armour` — project-wide full hardening pass
- `/forge-armour --scope <MOD>` — module-focused pass
- `/forge-armour --scope <atom>` — narrow advisory pass for one atom
- `/forge-armour --advisory` — allow review even when audit gate is not clean

Auto-triggering is optional. If implemented later, it should fire only after `forge-audit` passes cleanly or after the human explicitly opts into the extra gate.

---

## 4. Security profile interview

Before proposing controls, the skill should establish the security profile. This is the minimum context needed to avoid shallow or generic recommendations.

Required dimensions:
- data sensitivity classes
- actor classes and trust boundaries
- tenancy model
- interface exposure model
- authentication model
- authorization model
- compliance and contractual drivers
- operational risk posture
- top abuse cases

Output artifact:
- `<spec-dir>/security-profile.md`

This file should be short, durable, and decision-oriented. It is not a compliance essay. It exists so future audit, armour, and implementation sessions can see the assumptions that justify the controls.

---

## 5. The 8 armour passes

### Pass 1 — Exposure and trust-boundary mapping

Build a map of:
- external entry points
- internal-only module seams
- privileged actor paths
- third-party trust edges

The pass should detect where the spec handles sensitive transitions without explicitly describing the control model.

Typical findings:
- public API entry with no auth requirement
- admin path treated like ordinary user path
- external webhook or event source with no authenticity validation

### Pass 2 — Identity, authentication, and authorization coverage

This pass checks whether identity and authorization semantics are explicit enough to implement safely.

Typical findings:
- no default resource authorization model in `L1`
- module policies missing for privileged actions
- atom handles account/session/payment data without authz edge cases

### Pass 3 — Data protection and secrets handling

This pass checks whether the specs say enough about:
- secrets source and rotation
- redaction and logging boundaries
- encryption expectations
- token/session handling
- retention and deletion

Typical findings:
- PII or token paths with no redaction guidance
- secrets implied via module permissions but not governed
- sensitive data handling expressed atom-by-atom with no project-level convention

### Pass 4 — Multi-tenancy and isolation

Focus on shared-state risks.

Typical findings:
- shared datastore access with no tenant invariant
- reporting/export atoms with no tenant-bypass policy model
- maintenance jobs that can act across tenants without explicit authority

### Pass 5 — Abuse-case and misuse resistance

Think adversarially about misuse, not just nominal operation.

Typical probes:
- enumeration
- replay
- brute force
- unsafe retries
- forged events
- poisoned artifacts
- unsafe model prompting or model output handling

Typical findings:
- webhook consumer with no signature validation
- retrying payment-like action with no anti-replay control
- search or lookup endpoints that reveal existence information too freely

### Pass 6 — Supply chain and third-party dependency risk

Focus on the operational and dependency posture required to implement the specs safely.

Typical findings:
- critical third-party dependency with no resilience language
- deploy/runtime artifact handling with no provenance or integrity expectation
- L5 operations missing vulnerability-management or patching expectations

### Pass 7 — Detection, auditability, and response readiness

Ask whether the system would leave evidence if abused.

Typical findings:
- privileged state changes with no audit trigger
- no operator-observable security events
- security-relevant failures collapsed into generic operational errors

### Pass 8 — Recovery, resilience, and safe failure

Ask what happens when a security control or identity dependency fails.

Typical findings:
- auth provider outage with no declared fail-safe behavior
- no revocation/rotation posture for compromised credentials
- no break-glass guardrails

---

## 6. Severity and approval model

Severity tiers:
- `blocking`: major security gap; implementation should not proceed
- `high`: material hardening gap
- `medium`: important, but not gate-blocking by itself
- `low`: defense-in-depth or hygiene

Approval rules:
- analysis requires no approval
- every write requires explicit approval
- bulk approval is allowed only after the write set is described clearly
- rejected controls should be recorded with rationale

If the human chooses to accept risk, the skill records:
- the risk summary
- the rejected control
- the rationale
- optional revisit date

---

## 7. Preferred mutation targets

The skill should prefer the highest-leverage layer that solves the problem.

Mutation priority:
1. `security-profile.md`
2. `L1_conventions.yaml`
3. `L2_modules/*.yaml`
4. `L2_policies/*.yaml`
5. `L5_operations.yaml`
6. `L3_atoms/*.yaml`

Rationale:
- project posture belongs in `L1` and `L5`
- repeated control requirements belong in module policies
- atom-level edits are for local invariants, abuse cases, and edge handling

---

## 8. Non-goals

`forge-armour` does not:
- implement code
- replace threat modeling workshops entirely
- guarantee compliance certification
- create architecture unrelated to demonstrated risk
- bypass creator skills when new structure is required

If a fix requires new domain structure, route back to:
- `forge-discover` for project conventions or major structural changes
- `forge-decompose` for missing atoms
- `forge-atom` for under-specified atom contracts

---

## 9. Durable artifacts

Recommended artifacts:
- `security-profile.md`
- `armour-YYYY-MM-DD.md`
- `armour-history.md`

These artifacts let later sessions understand:
- what security assumptions were adopted
- what findings were raised
- what was changed
- what risks were accepted

---

## 10. Design guidance drawn from the security skill corpus

The external cybersecurity-skill corpus is broad and useful, but `forge-armour` should borrow its **control families**, not its prose style.

Control families repeatedly reinforced across the sampled corpus:
- least privilege
- explicit trust-boundary treatment
- secrets management and rotation
- auditability and continuous monitoring
- data minimization and redaction
- strong authn/authz semantics
- resilience against replay, brute force, spoofing, and abuse
- supply-chain integrity and patch posture

`forge-armour` should map these into Forge-native spec surfaces instead of reproducing long procedural security runbooks.
