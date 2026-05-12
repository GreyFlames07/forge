# Minimal Full Stack

This is a committed Forge V2 example project.

What it demonstrates:

- a `full-stack` profile with separate `app` and `api` units
- bootstrap slice: dashboard route -> dashboard flow -> app/api operations -> main store
- adjacent slice: profile overview reusing the same shared runtime units and store
- explicit contract relationships including input, output, and referenced types

Quick checks:

```bash
../../.venv/bin/forge list --forge-dir forge
../../.venv/bin/forge context load_dashboard --forge-dir forge
../../.venv/bin/forge graph --forge-dir forge --no-open
```
