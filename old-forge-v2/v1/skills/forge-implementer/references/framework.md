# forge-implementer — Framework

Reference for judgment calls about minimality, architecture conflicts, and implementation decisions not resolved by the orchestrator prompt.

## Contents

| § | Section |
|---|---|
| §1 | Minimality — what it means |
| §2 | Architecture conflict — when to set it |
| §3 | Isolation — why tests are never read |

---

## 1. Minimality — what it means

Minimality is a hard constraint, not a style preference. Produce exactly what the spec requires, nothing more.

**Allowed:**
- One function / class / file per atom (unless architecture naming policy says otherwise)
- Imports required to implement declared `CALL` steps and side-effect markers
- Error handling exactly as declared in `output.errors` and `failure_modes`
- DI scaffolding only when the architecture block explicitly requires a DI pattern
- Framework boilerplate required by the architecture's framework (e.g., NestJS `@Controller`)

**Forbidden:**
- Generic catch-alls beyond declared error codes
- Helper utilities not referenced by any spec element
- Service locators, registries, or containers beyond what the stated DI strategy requires
- Logging beyond what L1 conventions declare (`on_entry`, `on_success`, `on_failure` templates only)
- Abstract base classes or type hierarchies not implied by the type system or framework
- Feature flags or env-var branching not in the spec

**Rule of thumb:** if you cannot point to a specific spec element — logic step, side_effect marker, invariant, error code, declared type — that justifies a line of code, that line does not belong.

---

## 2. Architecture conflict — when to set it

Set `architecture_conflict: true` when the spec requires a decision the architecture block is silent on AND the decision is not inferrable from the tech stack. Return without writing files.

**Decisions that need explicit architecture guidance:**
- Async vs. sync (spec has `EMITS_EVENT` or long-running ops but architecture is silent)
- Error return style (exceptions vs. Result/Either — state it; don't guess)
- DI pattern for CALL steps — default is direct import unless architecture states otherwise
- Schema/migration tool — required for DECLARATIVE atoms with `target: database_schema`
- IaC tool — required for DECLARATIVE atoms with `target: infrastructure`
- UI framework — required for COMPONENT atoms

**Safe defaults (infer without conflict):**
- Language-native async when the language defaults to async (Node.js, Python asyncio)
- Direct imports for CALL steps when `dependency_injection: direct_imports`
- Language error handling idioms when `error_handling` pattern is explicitly stated

When in doubt, prefer `architecture_conflict: true` over guessing. A wrong implementation is harder to fix than a conflict signal — the orchestrator surfaces it to the human and re-invokes.

---

## 3. Isolation — why tests are never read

forge-implementer never reads test files. This is structural.

The test-before-implementation pipeline exists so:
1. Tests are written against the spec, not against an implementation
2. Implementation is written against the spec, not against the tests
3. The red-green cycle reveals genuine spec coverage gaps

If the implementer reads tests, it short-circuits the spec-driven loop — producing code that makes tests pass rather than code that satisfies the spec. These diverge when tests are incomplete.

The only feedback that reaches the implementer from the test phase is the orchestrator's `retry_feedback` — sanitized output with spec-linked hints pointing back to specific spec elements. Treat this as a pointer to the spec, not as a test description.
