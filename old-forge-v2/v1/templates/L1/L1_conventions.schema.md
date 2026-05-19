# L1 — Conventions Schema

**Purpose**: Project-wide defaults for frame logic. Atoms inherit these rules and override only by exception.

**Scope**: Project-global.

**File format**: YAML. Located at `L1_conventions.yaml` (project root). Singleton — no directory wrapper.

---

## Top-level structure

```yaml
observability: { ... }
failure:       { ... }
audit:         { ... }
security:      { ... }
verification:  { ... }
idempotency:   { ... }
overrides:     { ... }
```

All seven sections mandatory.

Platform-level concerns (deployment, rate limiting, event semantics) live in L5 Operations, not here.

---

## L1.1 — observability

```yaml
observability:
  logging:
    default_level:  DEBUG | INFO | WARN | ERROR | FATAL
    on_entry:       <template_string>
    on_success:     <template_string>
    on_failure:     <template_string>
    level_map:
      <error_category>: DEBUG | INFO | WARN | ERROR | FATAL
  tracing:
    span_name_template: <template_string>
    propagate:          <boolean>
```

`default_level` applies to `on_entry` and `on_success` logging. `level_map` applies to `on_failure` logging, keyed by error category.

Template variables available in log strings: `{atom_id}`, `{owner_module}`, `{input_summary}`, `{output_summary}`, `{error_code}`, `{duration_ms}`, `{actor}`, `{trace_id}`.

---

## L1.2 — failure

```yaml
failure:
  defaults:
    <error_category>:
      action:  return_to_caller | retry | circuit_breaker | dead_letter | halt_and_alert
      retries: <integer>             # required when action is retry; omit otherwise
      backoff: constant | linear | exponential  # required when action is retry; omit otherwise
  propagation:
    wrap_unexpected: <boolean>
    unexpected_code: <error_code>
```

One entry per error category declared in L0.2. Missing categories inherit a safe default (`return_to_caller`).

`retries` and `backoff` are required when `action` is `retry` or `circuit_breaker`, and must be omitted otherwise.

---

## L1.3 — audit

```yaml
audit:
  triggers:
    side_effect_markers: [<marker>, ...]
  entry_shape:
    fields: [<field_name>, ...]
  sink:
    kind:   db_table | event_stream | file
    target: <string>
```

All markers referenced here must exist in L0.6 (`side_effect_markers`).

---

## L1.4 — security

```yaml
security:
  default_posture:
    authentication: required | optional | none
    auth_methods:   [<method>, ...]
    roles:          [<role_name>, ...]
  roles:
    <role_name>: <description>
  resource_authorization:
    ownership_check_required_for_markers: [<marker>, ...]
    ownership_field:                       <string>
    admin_bypass:                          <boolean>
```

Recognized auth methods: `bearer`, `api_key`, `oauth2`, `session`, `mtls`, `hmac`, `none`.

`resource_authorization` declares the project-wide convention for resource-level access control (beyond role checks). Atoms whose side-effect markers intersect with `ownership_check_required_for_markers` must verify the calling actor owns the target resource before mutating, unless the actor's role is in the admin bypass set. `ownership_field` names the conventional field on owned entities (typically `owner_id`, `user_id`, or `tenant_id`).

No enumeration of interface kinds. Kind-specific posture overrides happen at L2.

---

## L1.5 — verification

```yaml
verification:
  floors:
    min_property_assertions: <integer>
    min_edge_cases:          <integer>
    min_example_cases:       <integer>
```

Three universal floors. Kind-specific required sections are declared in L3 kind schemas, not here.

---

## L1.6 — idempotency

```yaml
idempotency:
  key_source:
    required_for_markers: [<marker>, ...]
    key_field:            <string>
  dedup:
    strategy: database | cache | none
    ttl_sec:  <integer>
```

All markers referenced here must exist in L0.6 (`side_effect_markers`).

---

## L1.7 — overrides

```yaml
overrides:
  allowed_fields:
    - <dotted.field.path>
    ...
  requires_justification: <boolean>
```

Declares which L1 convention fields an atom (L3) may override in its own spec. Any atom-level override must target a field listed here. If `requires_justification` is `true`, the atom must include a human-readable `justification` string with each override.

Path patterns in `allowed_fields` may use `<category>` as a placeholder that matches any value from L0 `error_categories`. For example, `failure.defaults.<category>.retries` is matched by atom overrides like `failure.defaults.NET.retries` or `failure.defaults.EXT.retries`.

---

## Validation rules

1. All seven sections present.
2. Every error category in `failure.defaults` exists as a key in L0 `error_categories`.
3. `failure.propagation.unexpected_code` exists as a key in L0 `errors`.
4. Every `level_map` key exists as a key in L0 `error_categories`.
5. Every `level_map` value is a valid log level (`DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`).
6. `default_level` is a valid log level.
7. Every side-effect marker referenced in `audit` or `idempotency` exists as a key in L0 `side_effect_markers`.
8. Every role referenced in `default_posture.roles` exists in `security.roles`.
9. Every auth method in `default_posture.auth_methods` is one of the recognized values.
10. `idempotency.key_field` is non-empty.
11. `retries` and `backoff` are present when `action` is `retry` or `circuit_breaker`, absent otherwise.
12. Every path in `overrides.allowed_fields` is a valid dotted path to a field defined in this schema.
13. Every `{variable}` token in `observability.logging.on_entry`, `on_success`, `on_failure`, and `observability.tracing.span_name_template` is one of the declared template variables: `{atom_id}`, `{owner_module}`, `{input_summary}`, `{output_summary}`, `{error_code}`, `{duration_ms}`, `{actor}`, `{trace_id}`.
14. Every marker in `security.resource_authorization.ownership_check_required_for_markers` exists as a key in L0 `side_effect_markers`.
15. Every role referenced anywhere in L1 exists in `security.roles`.
16. No atom kinds or interface kinds appear anywhere in L1.
