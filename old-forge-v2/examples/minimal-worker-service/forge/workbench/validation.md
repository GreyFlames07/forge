# Validation Report

## Schema Validation
- PASS: schema references and required fields are coherent

## Runtime-Aware Checks
- PASS: unit `worker` entrypoint exists at apps/worker/src/main.py

## Declared Verification Checks
- PASS: startup `worker_health` :: `python3 apps/worker/src/main.py --healthcheck` -> worker-ok

## Flow Workflow Checks
- INFO: flow `run_demo_job_flow` requires workflow confirmation: Confirm the worker run-once command prints the processed result payload.

## Operator Workflow Checks
- run_demo_job_flow: Confirm the worker run-once command prints the processed result payload. :: Run python3 apps/worker/src/main.py --run-once and verify the output contains job and result fields.
