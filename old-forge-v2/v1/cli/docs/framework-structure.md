# Framework Structure

Defines the file layout, naming conventions, and directory rules for a Forge project.

---

## Spec Root

All spec files live under `spec/` at the project root.

```
<project-root>/
├── spec/
│   ├── conception.yaml
│   └── <system>/
└── src/
```

---

## Directory Layout

```
spec/
├── conception.yaml                              # singleton; actors and glossary inline

└── <system>/
    ├── system.yaml                              # singleton per system

    ├── types/
    │   └── <TypeName>.yaml                     # one file per type

    ├── errors/
    │   └── <ErrorName>.yaml                    # one file per error

    ├── policies/
    │   └── <policy>.yaml                       # one file per policy

    ├── contracts/
    │   └── <contract>.yaml                     # one file per contract

    ├── integrations/
    │   └── <integration>.yaml                  # one file per integration

    ├── interactions/
    │   └── <interaction>.yaml                  # one file per interaction

    ├── flows/
    │   └── <flow>.yaml                         # one file per flow

    ├── implementation/
    │   ├── datastores.yaml                      # all datastores, separated by ---
    │   ├── tests.yaml                           # all tests, separated by ---
    │   ├── environments.yaml                    # all environments, separated by ---
    │   └── deployments.yaml                     # all deployments, separated by --- (optional)

    └── <domain>/
        ├── domain.yaml

        └── <module>/
            ├── module.yaml
            └── <element>.yaml                   # properties + operations inline
```

---

## File Naming

File names use the last segment of the node ID, preserving case.

| Node | File |
|------|------|
| Conception | `conception.yaml` |
| System | `<system>/system.yaml` |
| Type | `<system>/types/<TypeName>.yaml` |
| Error | `<system>/errors/<ErrorName>.yaml` |
| Policy | `<system>/policies/<policy>.yaml` |
| Contract | `<system>/contracts/<contract>.yaml` |
| Integration | `<system>/integrations/<integration>.yaml` |
| Interaction | `<system>/interactions/<interaction>.yaml` |
| Flow | `<system>/flows/<flow>.yaml` |
| Domain | `<system>/<domain>/domain.yaml` |
| Module | `<system>/<domain>/<module>/module.yaml` |
| Element | `<system>/<domain>/<module>/<element>.yaml` |
| Datastores | `<system>/implementation/datastores.yaml` |
| Tests | `<system>/implementation/tests.yaml` |
| Environments | `<system>/implementation/environments.yaml` |
| Deployments | `<system>/implementation/deployments.yaml` |

---

## Inline vs. Separate Files

**Inline in their parent file:**
- Actors and glossary terms — in `conception.yaml`
- Element properties and operations — in the element file
- Composite type properties — in the type file

**Flat multi-doc files** under `implementation/` (nodes separated by `---`):
- `datastores.yaml`, `tests.yaml`, `environments.yaml`, `deployments.yaml`

**One file per node** — everything else.

---

## ID Resolution

The CLI derives a node's full ID from its file path:

1. Read `conception.yaml` for the conception name.
2. Strip `spec/` prefix.
3. Strip role suffixes (`/system.yaml`, `/domain.yaml`, `/module.yaml`).
4. Strip `implementation/` segment from flat file paths.
5. Replace `/` with `.`, drop `.yaml`.
6. Prepend the conception name.

```
spec/shortener/links/link_manager/short_link.yaml
→ shortener/links/link_manager/short_link
→ linkhub.shortener.links.link_manager.short_link

spec/shortener/types/ShortCode.yaml
→ linkhub.shortener.types.ShortCode
```

---

## Multi-System Projects

Each system gets its own directory under `spec/`. Actors and glossary are defined once in `conception.yaml` and shared across all systems.

```
spec/
├── conception.yaml
├── shortener/
└── billing/
```

---

## Concrete Example — LinkHub - Do not reference in actual implementation

```
spec/
├── conception.yaml

└── shortener/
    ├── system.yaml

    ├── types/
    │   ├── ShortCode.yaml
    │   ├── URL.yaml
    │   ├── CountryCode.yaml
    │   ├── short_link_record.yaml
    │   ├── click_record.yaml
    │   ├── click_aggregate_record.yaml
    │   ├── create_link_input.yaml
    │   ├── redirect_request.yaml
    │   └── redirect_response.yaml

    ├── errors/
    │   ├── InvalidUrl.yaml
    │   └── LinkInactive.yaml

    ├── policies/
    │   ├── standard_encryption.yaml
    │   ├── creator_authenticated.yaml
    │   ├── audit_classified.yaml
    │   ├── analytics_classification.yaml
    │   └── redirect_sla.yaml

    ├── contracts/
    │   ├── create_short_link.yaml
    │   ├── resolve_short_link.yaml
    │   ├── redirect.yaml
    │   └── record_click.yaml

    ├── interactions/
    │   ├── redirect_resolves_link.yaml
    │   └── redirect_emits_click.yaml

    ├── flows/
    │   └── user_redirect.yaml

    ├── implementation/
    │   ├── datastores.yaml
    │   ├── tests.yaml
    │   ├── environments.yaml
    │   └── deployments.yaml

    ├── links/
    │   ├── domain.yaml
    │   └── link_manager/
    │       ├── module.yaml
    │       └── short_link.yaml

    ├── traffic/
    │   ├── domain.yaml
    │   ├── redirector/
    │   │   ├── module.yaml
    │   │   └── redirector.yaml
    │   └── click_recorder/
    │       ├── module.yaml
    │       └── click.yaml

    └── analytics/
        ├── domain.yaml
        └── aggregator/
            ├── module.yaml
            └── aggregate.yaml
```

---

## Validation Rules

1. `conception.yaml` exists at `spec/` root. Exactly one per project.
2. Every `system.yaml`, `domain.yaml`, and `module.yaml` is the sole file of that name in its directory.
3. Every node `id` field matches its path-derived ID.
4. Every ID referenced anywhere in the spec resolves to an existing node.
5. No two files produce the same derived ID.
6. Element files contain only inline properties and operations — no nested element files.
7. Registry directories (`types/`, `errors/`, `policies/`, `contracts/`, `integrations/`, `interactions/`, `flows/`) exist only directly under a system directory.
8. `implementation/` exists only directly under a system directory and contains only `datastores.yaml`, `tests.yaml`, `environments.yaml`, and `deployments.yaml`.
