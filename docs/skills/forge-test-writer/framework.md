# forge-test-writer — Framework

Reference for the test philosophy behind forge-test-writer's rules. Read when you need to make judgment calls about what makes a test correct, complete, or live.

## Contents

| § | Section |
|---|---|
| §1 | Why integration and system tests run live |
| §2 | Contextual not generic — what it means |
| §3 | Test pyramid summary |
| §4 | Exhaustiveness vs. minimality |

---

## 1. Why integration and system tests run live

Integration tests (flows) and system tests (journeys) run against a live system with no internal mocks. This is intentional.

**The problem with internal mocks at integration level:** A mock replaces an atom or module with a stub returning expected values. The test passes even when the real integration is broken. Integration tests exist specifically to catch integration failures — mocking internals defeats that purpose.

**What this means in practice:**
- System starts as a real process via `run_command` from `L5_operations.yaml`
- HTTP calls go to real routes, not test doubles
- DB writes actually write to a test database
- Events are published to a real test broker
- The test verifies the end-to-end chain

**The only acceptable mocks at integration/system level:** genuine third-party external APIs (Stripe, Twilio, SendGrid, etc.) declared in `L0.external_schemas`. Mock these with test-mode credentials, local fakes (Stripe CLI, Wiremock), or sandbox environments — they are outside the system boundary and cannot be live in CI.

---

## 2. Contextual not generic — what it means

Test inputs and expected outputs must come from the spec's concrete values, not from placeholder imagination.

**Generic (wrong):**
```typescript
// BAD — "user-1" and 100 are not in the spec
test("creates order", async () => {
  const result = await createOrder({ customerId: "user-1", amount: 100 });
  expect(result.status).toBe("success");
});
```

**Contextual (correct):**
```typescript
// Derived from atm.ord.create_order.verification.example_cases[0]
test("test_unit_example_case_happy_path", async () => {
  const result = await createOrder({ customerId: "c_123", amount: 4999 });
  expect(result.orderId).toBeDefined();
  expect(result.status).toBe("pending");
});
```

**How to find domain values:**
- `verification.example_cases[*].input` and `.expected_output` — use verbatim
- `verification.edge_cases[*]` — derive inputs from the case description
- `failure_modes[*].trigger` — construct conditions that match the trigger
- `invariants.pre[*]` — construct inputs that violate the invariant to test guard clauses
- L0 constants referenced in the spec — import the constant, never hardcode the literal value

If no concrete value is available for a field, use a value clearly within the field's declared type and nullability — not a placeholder string like `"foo"` or `"test@test.com"`.

---

## 3. Test pyramid summary

| Level | Entity | Scope | Mocks allowed |
|---|---|---|---|
| unit | atom | one atom in isolation | called atoms (contract mocks using declared signature), genuine external APIs |
| integration | flow | live system; real HTTP/CLI/broker invocations | genuine third-party external APIs only |
| system | journey | full E2E; browser/CLI/API client drives all transitions | genuine third-party external APIs only |

Unit tests mock called atoms using their declared signatures from `forge inspect`. Integration and system tests mock nothing internal.

---

## 4. Exhaustiveness vs. minimality

These are not in tension. Exhaustiveness = cover every declared spec element. Minimality = don't invent spec elements.

One test per declared spec element. Not two. Not zero.

If two spec elements (e.g., near-duplicate failure modes) produce no testable behavioral difference, write one test covering both and link both in the audit file row. Note the decision in the audit file. Do not silently omit one.

If the spec has no `verification` entries, generate tests from `logic` branches + `failure_modes` + `invariants` + `side_effects`. Flag the thin verification in the report summary.
