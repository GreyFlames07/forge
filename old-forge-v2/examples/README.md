# Forge V2 Examples

This directory contains three committed example projects you can test the Forge V2 CLI against:

- `minimal-full-stack/` - a minimal full-stack schema with a tiny Python HTTP backend and static frontend shell
- `minimal-cli/` - a minimal CLI project with a runnable bootstrap command
- `minimal-worker-service/` - a minimal worker-style project with a runnable background bootstrap command

Each example is intentionally shaped as a progression story:

- a bootstrap slice that proves the first runnable path
- at least one adjacent slice that expands capability without redefining the runtime
- vendored docs, frameworks, and agent skills so the example matches `forge init`

Useful smoke tests:

```bash
./.venv/bin/forge list --forge-dir examples/minimal-full-stack/forge
./.venv/bin/forge context load_dashboard --forge-dir examples/minimal-full-stack/forge
./.venv/bin/forge graph --forge-dir examples/minimal-full-stack/forge --no-open

./.venv/bin/forge list --forge-dir examples/minimal-cli/forge
./.venv/bin/forge list --forge-dir examples/minimal-worker-service/forge
```
