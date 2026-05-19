# Validation Report

## Schema Validation
- PASS: schema references and required fields are coherent

## Runtime-Aware Checks
- PASS: unit `cli` entrypoint exists at apps/cli/src/main.py

## Declared Verification Checks
- PASS: startup `cli_health` :: `python3 apps/cli/src/main.py health` -> ok

## Flow Workflow Checks
- INFO: flow `cli_report_flow` requires workflow confirmation: Confirm the CLI report command prints the expected JSON payload.
- INFO: flow `cli_status_flow` requires workflow confirmation: Confirm the CLI status command prints the expected JSON payload.

## Operator Workflow Checks
- cli_report_flow: Confirm the CLI report command prints the expected JSON payload. :: Run python3 apps/cli/src/main.py report and verify the output contains report and status fields.
- cli_status_flow: Confirm the CLI status command prints the expected JSON payload. :: Run python3 apps/cli/src/main.py status and verify the output contains status and source fields.
