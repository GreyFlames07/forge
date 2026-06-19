# Forge V4 Refactor Summary

## What Has Been Done

### V4 Schema And Documentation

- Added `FRAMEWORK_V4.md` and `SCHEMA_REFERENCE_V4.md` for the V4 system model.
- Kept V3 framework/schema references updated so existing V3 behavior remains documented.
- Added a minimal V4 example application under `examples/forge_minimal_web_app`.
- Added central V4 schema files in the example `forge/` directory:
  - `system.yaml`
  - `containers.yaml`
  - `entities.yaml`
  - `crawler.yaml`

### Crawler

- Added a Forge V4 crawler that reads a central Forge schema and source-root annotations.
- Added configurable comment parsing through `forge/crawler.yaml`.
- Added support for line-comment annotation profiles across common file types.
- Added structured, clean crawler failures for malformed annotations.
- Added skipped-file warnings for unsupported file/comment types.
- Added duplicate annotation detection as validation findings.
- Added extracted model output with system, containers, flows, entities, components, data shapes, persistence, operations, warnings, and findings.
- Added `forge crawl` with `json`, `yaml`, and `md` output formats.

### V4 Context Support

- Extended `forge context` to use the V4 crawler when a V4 project is detected.
- Added V4 context targets for:
  - system
  - container
  - container flow
  - entity
  - component
  - operation
  - data shape

### Init Support

- Added `forge init --schema-version v4`.
- Added V4 scaffold output for central Forge files and crawler configuration.

### Audit Webserver

- Updated the audit server so V4 projects render from crawler output.
- Added live rerender/version polling for schema and annotation changes.
- Replaced custom ELK rendering paths with Mermaid-based charts.
- Removed the Overview and Deployment tabs for V4 audit output.
- Merged deployment configuration into Runtime through an environment dropdown.
- Rendered runtime topology as unique directed container connections without edge numbering.
- Added compact runtime container cards with deployment details by environment.
- Rendered system business actions as compact rows.
- Added compact, progressive entity detail rendering with:
  - metadata rows
  - lifecycle diagrams
  - expandable transition details
  - related data shape rows
  - persistence rows
  - raw payloads behind disclosure
- Rendered container components, data shapes, and operations as compact rows with progressive disclosure.
- Reworked V4 flow pages:
  - kept numbered flow diagrams
  - replaced tables with compact stepped rows
  - kept flow row summaries minimal
  - moved input/output and logic into expansion
  - grouped step operations by container and local flow
  - moved operation input/returns into expansion as bullet points

### Tests

- Added crawler tests for V4 extraction, annotation parsing, skipped-file warnings, custom comment profiles, malformed annotation failures, duplicate findings, Forge markdown docs, V4 context, and V4 audit rendering.
- Updated existing audit tests for the V4 audit navigation changes.
- Current verification before this summary:
  - `python -m ruff check src/cli/commands/audit.py` passed in the project virtualenv.
  - `python -m pytest` passed with 35 tests.

## What Is Left To Do

- Decide the final V4 schema contract for container-flow step ownership:
  - The UI currently groups operations by container and local flow.
  - The schema may still need clearer semantics for source-side versus target-side local work inside a boundary step.
- Add stronger tests for the progressive flow UI structure:
  - closed rows contain only step number and runtime edge
  - expanded rows contain input/output, logic, local flow groups, and operation details
  - operation summaries do not leak input/returns
- Add tests for the audit server live reload path beyond static artifact assertions.
- Add crawler tests for more comment profiles and mixed-language repositories.
- Decide whether Forge markdown documents should have richer rendering than source listing inside the audit server.
- Review the remaining V4 audit styling against the V3 UI reference and continue tightening dense views.
- Add user-facing documentation for authoring annotations in code.
- Add release notes and migration guidance from V3 to V4.
- Review the security skill submodule deletion separately before merging it into product work.

## Local Artifacts Excluded From The PR

The following local tool/runtime artifacts were present in the workspace but are not part of the V4 product change:

- `.claude/`
- `.codex/`
- `.playwright-mcp/`
- `.system/`
- `.vscode/`
- generated audit screenshots
- generated `forge-audit.html`

These are ignored so the PR contains only product code, tests, docs, and the V4 example project.
