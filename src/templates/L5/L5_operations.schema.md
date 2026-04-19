# L5 — Operations Schema

**Purpose**: Project-wide platform guarantees and runtime behavior. Declares how code moves to production, how traffic is protected, and what semantics the event substrate provides. Distinct from L1 conventions (which govern atom-level frame logic) and from L2 modules (which describe ownership and interfaces).

**Scope**: Project-global. One file per project.

**File format**: YAML. Located at `L5_operations.yaml` (project root). Singleton — no directory wrapper.

---

## Top-level structure

```yaml
deployment:       { ... }   # L5.1 — mandatory
rate_limiting:    { ... }   # L5.2 — mandatory
event_semantics:  { ... }   # L5.3 — mandatory
observability:    { ... }   # L5.4 — optional
```

Sections L5.1–L5.3 are mandatory. `observability` is optional — omit until the stack is decided.

---

## L5.1 — deployment

```yaml
deployment:
  platform:                                       # optional
    cloud:              <string>                  # free-form, e.g., aws, azure, gcp, multi, on_prem, hybrid
    primary_region:     <string>                  # optional, e.g., us-east-1
    additional_regions: [<string>, ...]           # optional
    default_compute:    <string>                  # optional, e.g., lambda, ecs-fargate, kubernetes
  environments: [<env_name>, ...]
  default_strategy: rolling | canary | blue_green | recreate
  canary_weights:   [<percent>, ...]              # required when default_strategy: canary
  rollback:
    automatic_on:   [<condition>, ...]
    manual_allowed: <boolean>
```

Declares how code moves from spec to running system.

`platform` is **optional**. When present, it records the project-wide deployment platform posture: cloud provider, primary region (and any additional regions), and the default compute model modules inherit unless they override via `tech_stack.compute`. Every sub-field of `platform` is itself optional — include only what's decided. Fields are free-form strings (no fixed enum) to accommodate the full range of cloud, compute, and region naming conventions across providers and on-prem / hybrid deployments.

`environments` lists the deployment targets. `default_strategy` applies to every module unless overridden at the module level. `canary_weights` is the progression of traffic percentages when strategy is `canary` (e.g., `[5, 25, 50, 100]`). `rollback.automatic_on` is a list of pseudo-formal conditions that trigger automatic rollback (e.g., `error_rate > 5% for 5min`, `p99_latency > 2x baseline for 10min`).

---

## L5.2 — rate_limiting

```yaml
rate_limiting:
  default:
    requests_per_minute: <integer>
    burst:               <integer>
  per_auth_method:
    <method>:
      requests_per_minute: <integer>
      burst:               <integer>
  scope: per_actor | per_ip | per_api_key | global
```

Project-wide rate limits applied at inbound entry points. `default` applies to any entry point not matched by a more specific rule. `per_auth_method` overrides by authentication scheme (typically authenticated callers get higher limits than anonymous). `scope` determines the counter identity — whether a limit is tracked per actor, per IP, per key, or globally. L2 entry points may further override.

Recognized auth method keys in `per_auth_method` are the same set declared in L1.4 `security`: `bearer`, `api_key`, `oauth2`, `session`, `mtls`, `hmac`, `none`.

---

## L5.3 — event_semantics

```yaml
event_semantics:
  delivery:            at_most_once | at_least_once | exactly_once
  ordering:            fifo_per_key | unordered
  default_parallelism: <integer>
  ordering_key_field:  <string>
```

Project-wide defaults for event-driven flow. `delivery` sets the default guarantee for L2 `event_consumer` entry points and L3 atoms carrying `EMITS_EVENT`. `ordering` declares whether events are processed FIFO within a partition key or without order constraint. `ordering_key_field` names the conventional field used to partition events when `ordering: fifo_per_key` (e.g., `customer_id`). L2 entry points may override per consumer.

---

## L5.4 — observability

```yaml
observability:                              # optional
  stack: <string>                           # observability backend, e.g., prometheus-alertmanager-grafana
  defaults:
    latency_p99_ms:       <integer>         # project-wide SLA floor; module SLAs narrow from this
    error_budget_percent: <number>          # % of requests allowed to fail per rolling window
    trace_sample_rate:    <number>          # 0.0–1.0
  modules:
    <MODULE_ID>:
      sla:
        latency_p99_ms:       <integer>     # overrides defaults.latency_p99_ms for this module
        error_budget_percent: <number>      # overrides defaults.error_budget_percent
      metrics:
        - name:    <string>                 # Prometheus metric name, snake_case
          type:    counter | gauge | histogram | summary
          labels:  [<string>, ...]
          buckets: [<number>, ...]          # histogram only; ascending positive numbers
      traces:
        sample_rate: <number>              # overrides defaults.trace_sample_rate for this module
      alerts:
        - name:     <string>
          expr:     <string>               # PromQL expression
          severity: critical | warning | info
          for:      <duration>             # e.g., 5m, 10m
          annotations:
            summary: <string>
            runbook: <string>              # optional URL
      atom_overrides:
        <atom_id>:                         # must be an atom owned by this module
          sla:
            latency_p99_ms:       <integer>
            error_budget_percent: <number>
          traces:
            sample_rate: <number>
```

The entire `observability` section is optional. When present:
- `stack` is required — identifies the observability backend so `forge-observe` can generate the right config format.
- `defaults` provides project-wide baselines; module-level values narrow them (a module SLA may not be looser than the project default).
- `modules` keys must match module IDs declared in L2.
- `atom_overrides` keys must match atom IDs declared in L3 whose `owner_module` matches the containing module key.
- `metrics`, `traces`, `alerts`, and `atom_overrides` are all independently optional within a module block.

---

## Validation rules

1. All three mandatory sections present (deployment, rate_limiting, event_semantics).
2. `deployment.environments` is non-empty.
3. If `deployment.default_strategy == canary`, `canary_weights` is present, non-empty, monotonically non-decreasing, and ends at `100`.
4. `deployment.default_strategy` is one of `rolling`, `canary`, `blue_green`, `recreate`.
5. `rate_limiting.default.requests_per_minute` is a positive integer. `rate_limiting.default.burst` is a positive integer ≥ `requests_per_minute`.
6. Every method key in `rate_limiting.per_auth_method` is one of the recognized auth methods declared in L1.4.
7. `rate_limiting.scope` is one of `per_actor`, `per_ip`, `per_api_key`, `global`.
8. `event_semantics.delivery` is one of `at_most_once`, `at_least_once`, `exactly_once`.
9. `event_semantics.ordering` is one of `fifo_per_key`, `unordered`.
10. If `event_semantics.ordering == fifo_per_key`, `ordering_key_field` is non-empty.
11. `event_semantics.default_parallelism` is a positive integer.
12. `deployment.platform` is optional. When present, each sub-field (`cloud`, `primary_region`, `additional_regions`, `default_compute`) is individually optional. Values are non-empty strings when included. No fixed enum for any sub-field.
13. If `observability` is present, `observability.stack` is a non-empty string.
14. `observability.defaults.latency_p99_ms`, when present, is a positive integer.
15. `observability.defaults.error_budget_percent`, when present, is a number in the range (0, 100].
16. `observability.defaults.trace_sample_rate`, when present, is a number in [0.0, 1.0].
17. Each key in `observability.modules` must match a module ID declared in L2.
18. Each `metrics[*].type` is one of `counter`, `gauge`, `histogram`, `summary`.
19. `histogram` metrics must declare `buckets` — a non-empty list of ascending positive numbers.
20. Alert `severity` is one of `critical`, `warning`, `info`.
21. Each key in `atom_overrides` must match an atom ID declared in L3 whose `owner_module` matches the containing module key.
