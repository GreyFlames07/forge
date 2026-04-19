# L5 Authoring Guide

L5 Operations declares three things: how code ships, how traffic is controlled, and what the event substrate guarantees. These are platform-level decisions — distinct from atom-level frame logic (L1) and module ownership (L2).

**Why L5 is separate from L1**: L1 conventions govern atom execution (logging, retries, audit, idempotency). L5 governs the operating environment around atoms (release strategy, traffic shaping, event delivery). Different teams often own them, and their change cadence differs sharply — L1 conventions are stable; L5 operations evolve with platform tooling.

---

## Section 1: deployment

### Purpose

How code moves from spec to running system. Declares environments, release strategy, and rollback policy once — modules inherit unless they have unusual needs.

### Fields

**`environments`**
- List of deployment targets. Typical: `[dev, staging, prod]`. Some projects add `qa`, `sandbox`, `preview`.
- The runtime uses this list to enforce that deploy pipelines cover every declared environment.

**`default_strategy`**
- `rolling` — gradually replace old instances with new. Safe for stateless services.
- `canary` — route a small percentage of traffic to the new version first, ramp up. Safest for traffic-facing services.
- `blue_green` — stand up a second environment, switch traffic atomically. Fast rollback.
- `recreate` — tear down old, stand up new. Brief downtime. Use for dev environments or stateful services that can't run two versions.

**`canary_weights`**
- Traffic progression when strategy is canary. `[5, 25, 50, 100]` means 5% → 25% → 50% → 100%. Each stage gates on rollback conditions.
- Required when `default_strategy: canary`.

**`rollback.automatic_on`**
- Conditions that trigger automatic rollback without operator action. Pseudo-formal. Typical: `error_rate > 5% for 5min`, `p99_latency > 2x baseline for 10min`, `crash_loop_detected`.

**`rollback.manual_allowed`**
- Whether operators can trigger rollback manually. Almost always `true`.

### When to override per module

Most modules inherit. A module with heavy per-release schema changes might want `blue_green`. A background worker with no user traffic might use `recreate`.

---

## Section 2: rate_limiting

### Purpose

Every inbound entry point needs protection against abuse and cascading failure. Per-atom rate limits scale poorly — declare defaults here and override in L2 only when justified.

### Fields

**`default.requests_per_minute`**
- Default sustained rate per scope. `60` is reasonable for user-facing APIs; `600` for authenticated service-to-service; `10` for anonymous.

**`default.burst`**
- Maximum short-term burst above sustained rate. Token-bucket semantics. Must be at least as large as `requests_per_minute`.

**`per_auth_method`**
- Overrides by authentication scheme. Authenticated traffic usually tolerated at higher rates than anonymous.
- Keys must be recognized auth methods (bearer, api_key, etc.) as declared in L1.4.

**`scope`**
- `per_actor` — tracked against the authenticated identity. Fair but needs auth.
- `per_ip` — tracked by source IP. Works for anonymous; breaks for shared outbound IPs.
- `per_api_key` — tracked by API key. Service-to-service fairness.
- `global` — single counter across all traffic. Backstop for total-capacity protection.

### Interaction with L2

L2 entry points may override: an API that calls expensive ML inference might pull limits down; a webhook receiver might have special exemptions. Override references live in the L2 security block alongside auth overrides.

---

## Section 3: event_semantics

### Purpose

Event-driven flows have three decisions that shape correctness: delivery guarantee, ordering, and parallelism. Declare defaults here so every `event_consumer` entry point and `EMITS_EVENT` atom knows what to expect.

### Fields

**`delivery`**
- `at_most_once` — consumer may miss events; never sees duplicates. Use only when missed events are acceptable (analytics, metrics).
- `at_least_once` — consumer never misses events; may see duplicates. Idempotent consumers handle this (most common choice).
- `exactly_once` — strongest guarantee. Usually requires specific infrastructure (transactional bus, outbox pattern). Expensive — only use when required.

**`ordering`**
- `fifo_per_key` — events with the same key field are processed in emission order. Events with different keys may interleave. Most systems want this for per-entity consistency.
- `unordered` — no order guarantee. Higher parallelism. Acceptable when events are commutative.

**`default_parallelism`**
- Number of concurrent consumer instances by default. Higher = more throughput, less ordering safety (unless partitioned by key).

**`ordering_key_field`**
- Conventional field used to partition events when `ordering: fifo_per_key`. `customer_id`, `order_id`, `tenant_id` — pick one that maps to most entities in your domain.
- Events without this field fall back to `unordered` semantics, which validators should warn about.

### Interaction with L1 and retries

`delivery: at_least_once` combined with L1.2 `failure.defaults.NET.action: retry` means consumers can see the same event multiple times. Consumer atoms must be idempotent — either marked `IDEMPOTENT` or verifying dedup via L1.6 idempotency keys. The validator cross-checks this.

---

## Section 4: observability

### Purpose

Declare where metrics, traces, and alerts live and what SLA each module is held to. L5 is the right home because observability posture (backend choice, retention, cardinality, sampling strategy) is owned by the same ops/platform team that owns deployment and rate limiting — it evolves with platform tooling, not with individual atom logic.

Distinct from L1.1 observability: L1.1 declares the _logging frame_ for atoms (log templates, levels, trace span names). L5.4 declares _platform-level targets_ (which stack, what SLAs, what metrics to emit, what alerts to fire). Different owners, different change cadence.

### Fields

**`stack`**
- Free-form string identifying the observability backend. Use `prometheus-alertmanager-grafana` for the open-source PAG stack. Other valid values: `datadog`, `grafana-cloud`, `newrelic`, `opentelemetry` (stack-agnostic collector). `forge-observe` uses this to pick the right output format when generating config files.

**`defaults`**
- Project-wide baselines all modules inherit unless they declare tighter values.
- `latency_p99_ms` — project-wide p99 latency budget in milliseconds. A module SLA may not be looser than this.
- `error_budget_percent` — percentage of requests allowed to fail per rolling evaluation window. Typical: `1.0` for internal services, `0.5` for payment-critical paths.
- `trace_sample_rate` — fraction of requests to trace end-to-end. `0.1` (10%) is a reasonable default; high-value atoms override to `1.0`.

**`modules.<MODULE_ID>`**
- Per-module observability block. Keys are the 3-letter module IDs from L2.
- `sla` — tighten (never loosen) the project defaults for this module.
- `metrics` — Prometheus metrics this module should emit. Declare intent here; `forge-observe` generates the recording rules and instrumentation guide.
  - `type: counter` — monotonically increasing (requests, errors, events emitted).
  - `type: gauge` — arbitrary up/down value (queue depth, active connections).
  - `type: histogram` — distribution with configurable buckets. Required for latency. Must declare `buckets`.
  - `type: summary` — pre-computed percentiles. Use histogram unless the client library forces summary.
- `traces.sample_rate` — override the default trace sample rate for this module.
- `alerts` — PromQL-driven alert rules. Each alert needs a `name`, `expr` (valid PromQL), `severity`, `for` (evaluation window), and at minimum a `summary` annotation. `runbook` is optional but strongly recommended for `critical` alerts.
- `atom_overrides` — fine-grain SLA or trace rate at the atom level. Only override when the atom has a materially different SLA than the rest of the module (e.g., the charge path vs a metadata read in the same PAY module).

### When to fill this in

Fill `stack` and `defaults` during `forge-discover` sub-phase 5 (platform posture). Fill module-level blocks progressively as modules are decomposed — you don't need to know all metrics upfront. Fill `atom_overrides` at `forge-atom` time when an atom's contract surface makes the per-atom SLA obvious (e.g., a card-charge atom is obviously tighter than a balance-read atom).

### Interaction with forge-validate and forge-observe

`forge-validate` Phase 4 reads this section to:
- Check live probe latencies against the resolved SLA (module default → atom override wins).
- Scrape `/metrics` if exposed and verify declared metric names and labels exist.

`forge-observe` reads the full section to generate:
- `observability/prometheus/rules.yaml` — recording + alert rules.
- `observability/alertmanager/alerts.yaml` — routing and grouping config.
- `observability/grafana/dashboard.json` — per-module dashboard scaffold.

---

## Common authoring mistakes

1. **Using `exactly_once` without required infrastructure.** It's not a flag you can set — it requires a transactional bus or outbox pattern. Without that, you get `at_least_once` dressed up. Verify your runtime actually supports it.
2. **Ordering: fifo_per_key without a stable key.** If `ordering_key_field: customer_id` but 30% of events lack a customer_id, 30% of your traffic silently loses ordering. Pick a key that's truly universal or adjust.
3. **Canary weights that don't reach 100.** `[5, 25, 50]` leaves half of traffic permanently on the old version. Always end at 100.
4. **Rollback triggers too tight.** `error_rate > 0.1%` will rollback on any transient blip. Use meaningful thresholds with time windows.
5. **Per-atom rate limiting.** Don't restate rate limits per atom — declare defaults here, override rare exceptions in L2 entry points.
