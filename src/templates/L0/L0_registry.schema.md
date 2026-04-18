# L0 — Registry Schema

**Purpose**: Definitional truth. Every name, type, error, event, constant, and external service reference used anywhere in the project resolves here. L0 is pure dependency infrastructure — the vocabulary the entire system is built from.

**Scope**: Project-global. Flat namespace.

**File format**: YAML. One file per project, located at `L0_registry.yaml` (project root). Singleton — no directory wrapper.

---

## Top-level structure

```yaml
naming_ledger:        { ... }   # L0.1
error_categories:     { ... }   # L0.2
errors:               { ... }   # L0.3
types:                { ... }   # L0.4
constants:            { ... }   # L0.5
side_effect_markers:  { ... }   # L0.6
external_schemas:     { ... }   # L0.7
```

All seven sections are mandatory. Empty sections are declared as `{}`.

---

## L0.1 — naming_ledger

```yaml
naming_ledger:
  module_id:    <regex>
  atom_id:      <regex>
  artifact_id:  <regex>
  flow_id:      <regex>
  journey_id:   <regex>
  type_id:      <regex>
  error_code:   <regex>
  event_name:   <regex>
  constant_id:  <regex>
  policy_id:    <regex>
```

All ten entity classes are mandatory.

---

## L0.2 — error_categories

```yaml
error_categories:
  <CATEGORY_CODE>: <description>
  ...
```

---

## L0.3 — errors

```yaml
errors:
  <ERROR_CODE>:
    message:   <string>
    category:  <CATEGORY_CODE>
    stability: stable | beta | deprecated       # optional, default: stable
    changelog:
      - version:     <string>
        date:        <YYYY-MM-DD>
        change_type: added | modified | deprecated | removed | fixed
        description: <string>
```

Every `category` value must exist as a key in `error_categories`.

---

## L0.4 — types

Each entry in `types` is either an entity or an enum, discriminated by `kind`.

### Entity form

```yaml
types:
  <type_id>:
    kind: entity
    stability: stable | beta | deprecated        # optional, default: stable
    fields:
      <field_name>:
        type:        <primitive | type_id>
        nullable:    <boolean>
        description: <string>        # optional
        default:     <value>         # optional
      ...
    invariants:                      # optional
      - <expression>
    changelog:
      - { version: ..., date: ..., change_type: ..., description: ... }
```

### Enum form

```yaml
types:
  <type_id>:
    kind: enum
    stability: stable | beta | deprecated        # optional, default: stable
    values: [<value1>, <value2>, ...]
    changelog:
      - { version: ..., date: ..., change_type: ..., description: ... }
```

### Allowed primitives

`string`, `integer`, `number`, `boolean`, `bigint`, `bytes`, `timestamp`, `uuid`.

---

## L0.5 — constants

```yaml
constants:
  <CONSTANT_ID>:
    value:       <literal>
    type:        <primitive | type_id>
    description: <string>
    stability:   stable | beta | deprecated        # optional, default: stable
    changelog:
      - { version: ..., date: ..., change_type: ..., description: ... }
```

---

## L0.6 — side_effect_markers

```yaml
side_effect_markers:
  <MARKER>: <description>
  ...
```

Recognized markers: `PURE`, `IDEMPOTENT`, `READS_DB`, `WRITES_DB`, `READS_CACHE`, `WRITES_CACHE`, `READS_FS`, `WRITES_FS`, `READS_ARTIFACT`, `EMITS_EVENT`, `CALLS_EXTERNAL`, `READS_CLOCK`.

Projects may extend this set. All markers referenced in L1 conventions, L3 atoms, or L4 orchestrations must exist here.

---

## L0.7 — external_schemas

```yaml
external_schemas:
  <schema_id>:
    provider:    <string>
    base_url:    <url>
    auth_method: bearer | hmac | oauth2 | api_key | mtls | none
    stability:   stable | beta | deprecated        # optional, default: stable
    changelog:
      - { version: ..., date: ..., change_type: ..., description: ... }
```

---

## Validation rules

A registry file is valid if and only if all of the following hold:

1. All ten naming_ledger entity classes are present and contain valid regex strings.
2. Every key in `errors` matches `naming_ledger.error_code`.
3. Every `errors.<code>.category` value exists as a key in `error_categories`.
4. Every key in `types` matches `naming_ledger.type_id`.
5. Every key in `constants` matches `naming_ledger.constant_id`.
6. Every entity field whose `type` is a non-primitive resolves to an existing key in `types`.
7. Circular type references are permitted only if at least one edge in the cycle is nullable.
8. Every `constants.<id>.type` is either a primitive or an existing key in `types`.
9. Every `constants.<id>.value` conforms to the declared `type`:
   - For primitive types, the literal must match the primitive (e.g., an `integer` type requires a whole-number value; a `uuid` type requires a valid UUID string).
   - For enum types, the value must be one of the enum's declared values.
   - For entity types, the value must be a map whose fields satisfy the entity's field specs and invariants.
10. Every `external_schemas.<id>.auth_method` is one of the allowed values.
11. Every key in `side_effect_markers` is an uppercase string.
12. Every `stability` value (when present) is one of `stable`, `beta`, `deprecated`.
13. Every changelog entry contains all four required fields (`version`, `date`, `change_type`, `description`).
