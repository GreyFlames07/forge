from __future__ import annotations

from pathlib import Path

import yaml
import pytest


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    forge = root / "forge"
    (forge / "verticals").mkdir(parents=True)
    (forge / "units").mkdir()
    (forge / "types").mkdir()
    (forge / "operations").mkdir()
    (forge / "surfaces").mkdir()
    (forge / "stores").mkdir()
    (forge / "flows").mkdir()
    (forge / "verification" / "startup").mkdir(parents=True)
    (forge / "verification" / "surfaces").mkdir()
    (forge / "verification" / "flows").mkdir()
    (forge / "workbench").mkdir()
    (root / "apps" / "api" / "src").mkdir(parents=True)
    (root / "apps" / "api" / "src" / "main.txt").write_text("api entrypoint\n", encoding="utf-8")

    def write(path: Path, data: dict) -> None:
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, sort_keys=False)

    write(
        forge / "system.yaml",
        {
            "schema_version": "forge.v2",
            "system": {
                "id": "demo",
                "name": "Demo",
                "project_profile": "api-service",
                "description": "Demo system",
                "purpose": "Provide a minimal demo",
                "goals": ["boot"],
                "invariants": ["bootstrap must work"],
                "auth_contexts": [{"id": "session_user", "description": "Signed-in user"}],
                "security": {"posture": ["auth by default"], "data_handling": ["classify data"]},
                "environments": [{"id": "dev", "description": "Development"}],
                "promotion_stages": ["dev"],
            },
        },
    )
    write(
        forge / "bootstrap.yaml",
        {
            "bootstrap": {
                "description": "Boot the API",
                "required_units": ["api"],
                "required_stores": ["main"],
                "required_surfaces": ["health_http"],
                "path": ["health_http"],
                "success_criteria": ["health returns ok"],
                "preserve": True,
            }
        },
    )
    write(
        forge / "build_policy.yaml",
        {
            "build_policy": {
                "strategy": "vertical_first",
                "preserve_runnability": True,
                "completion_states": ["specified", "implemented", "verified"],
                "rules": ["No task may break bootstrap."],
            }
        },
    )
    write(
        forge / "verticals" / "core.yaml",
        {"id": "core", "name": "Core", "description": "Core capability", "purpose": "Serve health", "owned_by": "team", "invariants": []},
    )
    write(
        forge / "units" / "api.yaml",
        {
            "id": "api",
            "name": "API",
            "description": "API unit",
            "kind": "service",
            "purpose": "Serve requests",
            "owned_by": "team",
            "entrypoint": "apps/api/src/main.txt",
            "serves_verticals": ["core"],
            "run": {"dev": "uvicorn app:app", "test": "pytest", "prod": "run service"},
            "env": [],
            "depends_on": {"units": [], "stores": ["main"], "externals": []},
            "healthcheck": {"kind": "http", "target": "/health"},
            "promotion": {"independently_promotable": True, "notes": ""},
        },
    )
    write(
        forge / "types" / "HealthResponse.yaml",
        {
            "id": "HealthResponse",
            "vertical": "core",
            "name": "HealthResponse",
            "description": "Health response",
            "kind": "payload",
            "identity": {"mode": "none", "fields": []},
            "fields": [{"name": "status", "description": "Status field", "spec": "String; required"}],
            "data_classification": "public",
            "lifecycle": {"mutability": "immutable", "rebuildable": False, "retention": "ephemeral", "state_field": "", "states": [], "transitions": []},
            "persistence": {"authority": "derived", "store": "", "metadata_store": "", "payload_store": "", "consistency": "strong", "access_patterns": []},
            "invariants": [],
        },
    )
    write(
        forge / "operations" / "get_health.yaml",
        {
            "id": "get_health",
            "vertical": "core",
            "name": "Get Health",
            "description": "Return health",
            "purpose": "Show service health",
            "unit": "api",
            "inputs": [],
            "outputs": ["HealthResponse"],
            "referenced_types": [],
            "errors": [],
            "reads": {"types": [], "stores": []},
            "writes": {"types": [], "stores": []},
            "emits": [],
            "consumes": [],
            "auth": {"context": "session_user", "required": False},
            "behavior": {"idempotent": True, "retryable": True},
            "invariants": [],
        },
    )
    write(
        forge / "surfaces" / "health_http.yaml",
        {
            "id": "health_http",
            "vertical": "core",
            "name": "Health HTTP",
            "description": "Health route",
            "unit": "api",
            "transport": "http",
            "operation": "get_health",
            "binding": {"http": {"method": "GET", "path": "/health"}},
            "error_mappings": [],
            "auth": {"context": "session_user", "required": False},
            "behavior": {"idempotent": True, "retryable": True},
        },
    )
    write(
        forge / "stores" / "main.yaml",
        {
            "id": "main",
            "name": "Main",
            "description": "Main store",
            "class": "transactional",
            "dev": "sqlite",
            "test": "sqlite",
            "prod": "postgres",
            "guarantees": {"durability": "durable", "consistency": "strong"},
            "notes": "",
        },
    )
    write(
        forge / "verification" / "startup" / "api_health.yaml",
        {"id": "api_health", "unit": "api", "intent": "API starts", "check": "GET /health returns 200"},
    )
    write(
        forge / "verification" / "surfaces" / "health_surface.yaml",
        {"id": "health_surface", "surface": "health_http", "intent": "Health responds", "request": "GET /health", "expect": ["200"]},
    )
    write(forge / "verification" / "promotion_gates.yaml", {"dev": ["bootstrap succeeds"], "test": [], "prod": []})
    write(forge / "workbench" / "status.yaml", {"bootstrap_health": "unknown", "schema_coverage": "draft", "implementation_progress": "not_started", "validation_state": "not_run"})
    return root
