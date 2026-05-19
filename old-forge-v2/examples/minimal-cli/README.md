# Minimal CLI

This is a committed Forge V2 example project.

What it demonstrates:

- a `cli-tool` profile
- bootstrap slice: the first status command path
- adjacent slice: a second report-oriented command path
- a single runtime unit expanding capability through additional surfaces and operations

Quick checks:

```bash
../../.venv/bin/forge list --forge-dir forge
../../.venv/bin/forge context show_status --forge-dir forge
python3 apps/cli/src/main.py status
```
