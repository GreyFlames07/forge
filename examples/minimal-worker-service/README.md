# Minimal Worker Service

This is a committed Forge V2 example project.

What it demonstrates:

- a `worker-service` profile
- bootstrap slice: the first runnable background job path
- adjacent slice potential without changing the runtime profile
- workbench- and skill-oriented validation where operator confirmation matters

Quick checks:

```bash
../../.venv/bin/forge list --forge-dir forge
../../.venv/bin/forge context run_demo_job --forge-dir forge
python3 apps/worker/src/main.py --run-once
```
