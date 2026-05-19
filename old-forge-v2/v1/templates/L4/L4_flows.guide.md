# L4 Authoring Guide

L4 composes atoms into multi-step operations. Two constructs serve different purposes: orchestrations coordinate internal work; journeys map external-facing user paths.

---

## When to use Orchestration vs. Journey

**Orchestration** when:
- No user is directly involved in the flow.
- The flow coordinates multiple atoms with transaction/compensation semantics.
- The flow is triggered by an event, a schedule, or another flow.
- Examples: process a payment after order placed, run nightly data sync, handle webhook retry logic.

**Journey** when:
- A user, client, or external caller is driving the flow.
- The flow has observable states the user transitions between.
- The flow maps to screens, pages, API request sequences, or CLI sessions.
- Examples: signup flow, checkout flow, onboarding wizard, multi-step API integration.

**Both can reference each other.** A journey transition can invoke an orchestration (e.g., user clicks "pay" → journey invokes payment orchestration). An orchestration can be triggered by a journey event. They are peers.

---

## Orchestration Guide

### Trigger

Every orchestration starts somewhere. Four trigger kinds:

**`event`** — most common. An event on the bus triggers the flow. Declare the event name and payload type. The event must match the naming ledger and the payload type must resolve in L0.4.

**`invocation`** — the flow is called directly from an L2 interface entry point or from another flow. Declare the payload type.

**`scheduled`** — runs on a cron schedule. Declare the cron expression. No payload.

**`manual`** — triggered by an operator (e.g., via admin panel). No payload unless specified.

### Transaction Boundary

This is a correctness decision, not an implementation detail.

**`acid`** — all steps run in a single database transaction. If any step fails, everything rolls back automatically. Use when all steps hit the same database and you need all-or-nothing semantics. Simplest but most restrictive — cannot span external service calls. **Validator rule**: `acid` is only legal when all invoked atoms belong to modules that share persistence (the same module, or modules linked via `shared_with`). Acid across independently-owned databases is not achievable without a 2PC coordinator the framework does not assume exists — use `saga` instead.

**`saga`** — no global transaction. Each step may define a `compensation` atom. If step 4 fails, compensations for steps 3, 2, 1 are called in reverse order. Use when the flow spans multiple services, databases, or external calls. More complex but more flexible.

**`none`** — no rollback. If step 3 fails, steps 1 and 2 are already done and stay done. Use for flows where partial completion is acceptable (e.g., send notifications — if one fails, the others still went out).

### Sequence

Each step is one atom invocation. Keep steps focused:

**`step`** — unique label. Referenced in error handling and verification.

**`invoke`** — what to call. An atom ID for direct work, or a flow ID to nest orchestrations.

**`with`** — how to pass data. Reference `trigger.*` for the flow's initial payload, or `<step_label>.output.*` for a previous step's output. The validator checks that referenced fields exist and types are compatible.

**`on_error`** — what to do when this step fails. Map error codes (or patterns like `PAY.NET.*`) to actions. Common patterns:
- Transient errors (NET): `RETRY(max=3)`
- Business errors (BUS, VAL): `HALT` or `HALT_AND_EMIT`
- Partial completion: `COMPENSATE_AND_HALT` (saga only)
- Non-critical steps: `CONTINUE`

**`compensation`** — the undo atom. Called in reverse order if a later step fails. Only meaningful for saga flows. Must be a real atom that reverses this step's effects (e.g., `atm.inv.release_items` compensates `atm.inv.reserve_items`).

Set `compensation: null` explicitly when a step has no side effects (pure reads, validations). This documents the choice rather than leaving it ambiguous.

### State Transitions

Document how external state changes across the flow. This is not step-level — it's flow-level. "If the whole flow succeeds, order status becomes FULFILLED and event order.completed is emitted." "If charge fails, order status becomes PAYMENT_FAILED."

These are the observable outcomes someone monitoring the system would see.

### Verification Criteria

The definition of done. For each possible outcome of the flow, declare what must be true afterward.

Good verification criteria are specific and observable:
- "On success: charges table has a new row, inventory is reduced, confirmation email is sent."
- "On charge failure: no inventory change, no email, order marked PAYMENT_FAILED."
- "On fulfillment failure: charge is refunded via compensation, inventory restored, order marked REFUNDED."

---

## Journey Guide

### Surface

The medium determines what handlers look like:

- `web_ui` / `mobile_ui` — handlers are COMPONENT atoms (screens). Transitions are user actions (clicks, form submissions).
- `api` — handlers are PROCEDURAL atoms (endpoint handlers). Transitions are API calls.
- `cli` — handlers are PROCEDURAL atoms (command handlers). Transitions are command inputs.
- `conversation` — handlers are PROCEDURAL atoms (turn handlers). Transitions are user messages.
- `email_sequence` — handlers are PROCEDURAL atoms (email generators). Transitions are time-based or action-based (link clicked).

### Entry Point

Where the journey starts. Must align with an L2 interface entry point. If the L2 module declares `kind: web_journey_entry, endpoint: /signup, invokes: jrn.signup_flow`, then this journey's `entry_point.from` should be `/signup`.

### States and Handlers

Every state needs a handler. The handler binds the state to an atom — the thing that "runs" while the journey is in that state. For a web UI, the handler is the screen component. For an API, it's the endpoint logic.

`on_enter` and `on_exit` are optional hooks for state lifecycle. Use sparingly — most logic belongs in the handler atom or the transition. Set to `null` when unused so the reader doesn't have to wonder if the field is missing or deliberately empty.

### Transitions

The core of a journey. Each transition says: "when in state X, if event Y happens, (optionally do Z), then go to state W."

**`on`** — what triggers the transition:
- A user action: `submit_email`, `click_continue`, `upload_file`.
- A system event: `verification_link_clicked`, `payment_completed`.
- `"auto"` — transition immediately upon entering the `from` state. Use for states that redirect (e.g., after email verification, auto-transition to onboarding).

**`invoke`** — optional work during the transition. Call an atom to validate input, process a form, create a record. The atom's success/failure determines whether the transition completes. Set to `null` for pure state transitions that need no atom call.

**`on_error`** — what happens when the invoked atom fails:
- `STAY` — remain in current state. Show the error to the user. Most common for validation errors.
- `GOTO state=<state>` — redirect to a different state (e.g., error page, retry page).
- `ABORT` — end the journey abnormally.

**`with` reference forms:**

- `trigger.<field>` — journey's initiating payload.
- `handler.<field>` — current state's handler atom, typically its `local_state` or input.
- `previous_state.<field>` — captured from prior state's handler output.
- `event.<field>` — from the event that triggered the transition.

**`guards`** — conditions checked before the transition fires. If any guard fails, the transition doesn't happen. Use for conditional paths: "only transition to admin_dashboard if user.role == admin."

### Verification Criteria

For journeys, verification includes the path taken (sequence of states) and the end result.

Good journey verification:
- "User completing signup: EMAIL_ENTRY → PASSWORD_ENTRY → VERIFICATION_SENT → VERIFIED → DASHBOARD. Users table has new row with status ACTIVE."
- "User abandoning at password: EMAIL_ENTRY → PASSWORD_ENTRY (exit). No row in users table."
- "Expired verification link: VERIFICATION_SENT → EMAIL_ENTRY. Previous partial data cleared."

---

## Common Authoring Mistakes

1. **Orchestration without verification criteria.** "It works" is not a criterion. Specify observable database state, events emitted, and downstream effects for every outcome.
2. **Saga without compensation on side-effecting steps.** If step 2 writes to DB and step 3 fails, step 2's data is orphaned. Every side-effecting step in a saga needs a compensation atom.
3. **Journey with unreachable exit state.** If no chain of transitions connects the initial state to any exit state, the journey can never complete. Validator catches this.
4. **Journey with missing handler.** Every declared state must have a handler entry.
5. **Mixing orchestration and journey.** If there's no user involved, it's an orchestration. If a user is driving, it's a journey. Don't put user transitions in orchestrations or internal coordination in journeys.
6. **Overly complex orchestrations.** If a flow has 15+ steps, consider decomposing into nested orchestrations. Each orchestration should represent one coherent operation.
7. **Transitions without error handling.** If a transition invokes an atom, consider what happens on failure. Silent failures in journeys leave users stuck.
8. **Using GOTO excessively in orchestrations.** Linear flows are easier to reason about. GOTO is for genuine error recovery paths, not control flow.
9. **Leaving `compensation` and `invoke` implicit.** When a step needs no compensation or a transition needs no invocation, write `null` explicitly. Silent absence looks like an oversight.
