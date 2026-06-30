from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from cli.commands.audit import render_live_audit_html
from cli.crawler import crawl_project
from cli.forge import main

REPO_ROOT = Path(__file__).resolve().parents[1]
V4_EXAMPLE_ROOT = REPO_ROOT / "examples" / "forge_minimal_web_app"


def test_crawler_reads_v4_central_files_and_annotations() -> None:
    result = crawl_project(V4_EXAMPLE_ROOT)
    payload = result.to_dict()

    assert payload["schema"] == "forge.extracted_model"
    assert payload["system"]["id"] == "team_notes"
    assert payload["summary"] == {
        "containers": 3,
        "container_flows": 5,
        "entities": 3,
        "decisions": 3,
        "components": 12,
        "data_shapes": 33,
        "persistence": 3,
        "operations": 31,
        "knowledge": 10,
        "warnings": 0,
        "duplicate_findings": 0,
        "validation_findings": 0,
        "forge_docs": 0,
    }
    assert {container["id"] for container in payload["containers"]} == {
        "frontend_ui",
        "backend_api",
        "notes_db",
    }
    assert {doc["type"] for doc in payload["knowledge"]} == {
        "checklist",
        "glossary",
        "guide",
        "incident",
        "migration",
        "note",
        "review",
        "runbook",
        "test_suite",
    }


def test_crawler_preserves_nested_annotation_payloads() -> None:
    result = crawl_project(V4_EXAMPLE_ROOT)

    account_router = next(annotation for annotation in result.components if annotation.id == "account_router")
    assert account_router.payload["interface"]["kind"] == "router"
    assert account_router.payload["interface"]["container_flows"] == ["register_user", "sign_in_user"]

    request_shape = next(annotation for annotation in result.data_shapes if annotation.id == "authenticated_http_request")
    assert request_shape.payload["shape"] == {
        "headers": {"string": "string"},
        "body": {"string": "string"},
    }

    note_list = next(annotation for annotation in result.data_shapes if annotation.id == "note_list_response")
    assert note_list.payload["shape"]["notes"] == "[ref[note_record]]"


def test_crawler_normalizes_compact_operation_flow_step_refs() -> None:
    source = V4_EXAMPLE_ROOT / "apps" / "backend" / "src" / "api" / "account_router.py"
    text = source.read_text(encoding="utf-8")
    assert "container_flow: register_user:2" in text
    assert "local_flow: register_user_backend:1" in text
    assert "step: 1" not in text

    result = crawl_project(V4_EXAMPLE_ROOT)
    operation = next(annotation for annotation in result.operations if annotation.id == "handle_register_user")
    participation = operation.payload["participates_in"][0]

    assert participation["container_flow"] == "register_user"
    assert participation["step"] == 2
    assert participation["local_flow"] == "register_user_backend"
    assert participation["local_step"] == 1


def test_v4_example_concurrent_local_steps_are_independent() -> None:
    result = crawl_project(V4_EXAMPLE_ROOT)
    groups: dict[tuple[object, object, object, object], list[tuple[str, object, object]]] = {}

    for operation in result.operations:
        payload = operation.payload
        entries = [
            item
            for item in payload.get("participates_in", [])
            if isinstance(item, dict)
        ]
        for entry in entries:
            key = (
                entry.get("container_flow"),
                entry.get("step"),
                entry.get("local_flow"),
                entry.get("local_step"),
            )
            groups.setdefault(key, []).append((operation.id, payload.get("input"), entry.get("passes")))

    concurrent_groups = {key: items for key, items in groups.items() if len(items) > 1}

    assert set(concurrent_groups) == {("list_notes", 2, "list_notes_backend", 2)}
    for items in concurrent_groups.values():
        inputs = {item[1] for item in items}
        passes = {item[2] for item in items}
        assert inputs.isdisjoint(passes)


def test_crawler_reports_adjacent_same_container_runtime_steps(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    containers_path = copied_root / "forge" / "containers.yaml"
    payload = yaml.safe_load(containers_path.read_text(encoding="utf-8"))
    flow = next(item for item in payload["container_flows"] if item["id"] == "list_notes")
    flow["steps"].append(
        {
            "id": 4,
            "container": "frontend_ui",
            "input": "ref[note_list_response]",
            "output": "ref[note_list_response]",
            "logic": ["Apply client-side note list presentation state."],
        }
    )
    containers_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    result = crawl_project(copied_root).to_dict()

    assert {
        "kind": "container_flow",
        "id": "list_notes",
        "step": 4,
        "message": "Adjacent runtime steps in the same container should be merged into one step.",
    } in result["findings"]["invalid_flow_steps"]


def test_crawler_infers_container_from_most_specific_source_root() -> None:
    result = crawl_project(V4_EXAMPLE_ROOT)

    user_store = next(annotation for annotation in result.components if annotation.id == "user_store")
    account_service = next(annotation for annotation in result.components if annotation.id == "account_service")

    assert user_store.container == "notes_db"
    assert account_service.container == "backend_api"


def test_crawl_command_outputs_json(capsys) -> None:
    assert main(["crawl", "--project-dir", str(V4_EXAMPLE_ROOT)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "forge.extracted_model"
    assert payload["summary"]["components"] == 12
    assert payload["summary"]["operations"] == 31
    assert payload["summary"]["knowledge"] == 10
    assert payload["summary"]["validation_findings"] == 0


def test_crawler_reads_knowledge_docs(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    knowledge = copied_root / "forge" / "knowledge" / "runbooks" / "backend_api_drain.md"
    knowledge.parent.mkdir(parents=True, exist_ok=True)
    knowledge.write_text(
        """---
type: runbook
title: Backend API Drain
refs:
  - container:backend_api
tags:
  - production
status: accepted
updated: 2026-06-30
---

# Backend API Drain

Restart the backend API after draining traffic.
""",
        encoding="utf-8",
    )

    payload = crawl_project(copied_root).to_dict()

    assert payload["summary"]["knowledge"] == 11
    assert any(
        doc["title"] == "Backend API Drain"
        and doc["refs"] == ["container:backend_api"]
        and doc["updated"] == "2026-06-30"
        for doc in payload["knowledge"]
    )
    assert payload["findings"]["knowledge"] == []


def test_crawler_reports_invalid_knowledge_refs(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    knowledge = copied_root / "forge" / "knowledge" / "testing" / "broken.md"
    knowledge.parent.mkdir(parents=True, exist_ok=True)
    knowledge.write_text(
        """---
type: test_suite
title: Broken Knowledge
refs:
  - container:missing_api
  - bad-ref
---

Body.
""",
        encoding="utf-8",
    )

    findings = crawl_project(copied_root).to_dict()["findings"]["knowledge"]

    assert any(item["reference"] == "container:missing_api" for item in findings)
    assert any(item["reference"] == "bad-ref" for item in findings)


def test_crawler_reports_skipped_file_types_by_default(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    readme = copied_root / "apps" / "frontend" / "src" / "architecture.md"
    readme.write_text("# Architecture\n\nNot a C3 source by default.\n", encoding="utf-8")

    payload = crawl_project(copied_root).to_dict()

    assert payload["warnings"]["skipped_file_types"] == [
        {
            "extension": ".md",
            "count": 1,
            "reason": "No crawler comment profile configured for this file extension.",
        }
    ]


def test_crawler_uses_user_comment_profile_config(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    config_path = copied_root / "forge" / "crawler.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "schema": "forge.crawler",
                "crawler": {
                    "comment_profiles": {
                        "bang": {
                            "extensions": [".ex"],
                            "prefixes": ["!"],
                        }
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    source = copied_root / "apps" / "frontend" / "src" / "custom.ex"
    source.write_text(
        "\n".join(
            [
                "! @forge:component",
                "! id: custom_component",
                "! role: utility",
                "! description: Component parsed through user config.",
                "! data_shapes: []",
                "! responsibilities:",
                "!   - Prove custom comments work.",
            ]
        ),
        encoding="utf-8",
    )

    result = crawl_project(copied_root)

    custom_component = next(annotation for annotation in result.components if annotation.id == "custom_component")
    assert custom_component.container == "frontend_ui"


def test_crawl_command_fails_cleanly_for_malformed_annotation(tmp_path: Path, capsys) -> None:
    copied_root = _copy_v4_example(tmp_path)
    source = copied_root / "apps" / "frontend" / "src" / "broken.ts"
    source.write_text(
        "\n".join(
            [
                "// @forge:component",
                "// id: broken_component",
                "// responsibilities:",
                "//   - valid",
                "//     bad_indent: nope",
            ]
        ),
        encoding="utf-8",
    )

    assert main(["crawl", "--project-dir", str(copied_root)]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "error": {
            "code": "malformed_annotation",
            "message": "Forge annotation must parse as prefix-commented YAML.",
            "source": "apps/frontend/src/broken.ts",
            "line": 1,
            "annotation": "@forge:component",
        }
    }


def test_crawler_extracts_duplicates_as_findings(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    source = copied_root / "apps" / "frontend" / "src" / "duplicate.ts"
    source.write_text(
        "\n".join(
            [
                "// @forge:component",
                "// id: account_screen",
                "// role: utility",
                "// description: Duplicate component id.",
                "// data_shapes: []",
                "// responsibilities:",
                "//   - Prove duplicates are findings.",
            ]
        ),
        encoding="utf-8",
    )

    payload = crawl_project(copied_root).to_dict()

    assert payload["summary"]["duplicate_findings"] == 1
    assert payload["summary"]["validation_findings"] == 1
    assert payload["findings"]["duplicates"][0]["kind"] == "component"
    assert payload["findings"]["duplicates"][0]["id"] == "account_screen"


def test_crawler_collects_forge_markdown_docs_for_audit(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    doc = copied_root / "forge" / "AUDIT_NOTES.md"
    doc.write_text("# Audit Notes\n\nRender this in the audit server later.\n", encoding="utf-8")

    payload = crawl_project(copied_root).to_dict()

    assert payload["forge_docs"] == [{"source": "AUDIT_NOTES.md", "title": "Audit Notes"}]


def test_v4_context_returns_component_scope(capsys) -> None:
    assert main(["context", "--project-dir", str(V4_EXAMPLE_ROOT), "--component", "account_screen"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["target"]["type"] == "component"
    assert payload["artifacts"]["component"]["id"] == "account_screen"
    assert payload["artifacts"]["container"]["id"] == "frontend_ui"


def test_v4_audit_generates_artifact(tmp_path: Path, capsys) -> None:
    output = tmp_path / "v4-audit.html"

    assert main(["audit", "--project-dir", str(V4_EXAMPLE_ROOT), "--artifact", "--output", str(output), "--no-open"]) == 0

    text = output.read_text(encoding="utf-8")
    assert "team_notes" in text
    assert 'data-group="Overview"' not in text
    assert 'id="overview"' not in text
    assert "Forge V4 Audit" not in text
    assert 'data-group="System"' in text
    assert "Validation Findings" in text
    assert "Decision Log" in text
    validation_section = text[text.index('id="verticals-overview"') : text.index('id="quality-assurance-overview"')]
    assert validation_section.index("Decision Log") < validation_section.index("Security Surface")
    assert "runtime_flow_steps_are_container_scoped" in text
    assert "backend_password_hash_boundary" in text
    assert "note_access_requires_authenticated_member" in text
    assert "Structured decisions recorded for future schema, review, security, and build context." in text
    assert 'data-filter-value="accepted"' in text
    assert 'data-filter-value="proposed"' in text
    assert 'data-filter-value="forge-schema"' not in text
    assert "account_screen" in text
    assert "Flow Diagram: register_user" in text
    assert "team_notes / Flow: register_user" not in text
    assert "The orange trigger starts the flow. Runtime containers are shown as nodes." in text
    assert "flow-trigger-row" in text
    assert "flow-outcome-row" in text
    assert "flow-data-path-card" in text
    assert "flow-data-path-meta" in text
    assert 'aria-label="Data Path controls"' in text
    assert "registration_form_state" in text
    assert "user_registered" in text
    assert "registration_rejected" in text
    assert 'class="flow-step-list"' in text
    assert "Component operations in this step" in text
    assert "account_screen" in text
    assert "1. frontend_ui" not in text
    assert "3 operations · operation steps 1, 2, 3" in text
    assert "5 operations · operation steps 1, 2 (2 concurrent), 3, 4" in text
    assert "account_router" in text
    assert "account_repository" in text
    assert "account_service" in text
    assert "account_router --&gt; account_service" in text
    assert "account_service --&gt; account_repository" in text
    assert "user_store" in text
    assert "persist_user_record" in text
    assert "flow-operation-step-head" in text
    assert "flow-operation-dot" in text
    assert "flow-operation-step-badge" not in text
    assert "flow-operation-row" not in text
    assert "Passes ref[register_user_request] to account_router" in text
    assert "Passes ref[register_user_command] to account_service" in text
    assert "flow-operation-logic" in text
    assert "register_user_backend" in text
    assert "<th>Container Flow</th><th>Component Operation Flow</th><th>Passes</th>" in text
    assert "<td>register_user:2</td><td>register_user_backend:1</td><td>ref[register_user_command]</td>" in text
    assert "mermaid@10" in text
    assert "frontend_ui[&quot;frontend_ui&quot;]" in text
    assert "backend_api[&quot;backend_api&quot;]" in text
    assert "notes_db[(&quot;notes_db&quot;)]" in text
    assert "class notes_db forgeDatabase" in text
    assert "frontend_ui --&gt; backend_api" in text
    assert "backend_api --&gt; notes_db" in text
    assert "notes_db --&gt; backend_api" in text
    assert "backend_api --&gt; frontend_ui" in text
    assert "frontend_ui --&gt; notes_db" not in text
    assert "|&quot;step " not in text
    assert "Runtime Edge Legend" not in text
    assert "Runtime Topology" in text
    assert "Unique directed connections between runtime containers" in text
    assert "visitor -.-&gt; team_notes" in text
    assert "visitor -.->|&quot;interacts&quot;| team_notes" not in text
    assert "business-action-table" in text
    assert "business-action-row" in text
    assert "<span role=\"columnheader\">Action</span>" in text
    assert "<span role=\"columnheader\">Actor</span>" in text
    assert "<span role=\"columnheader\">Results</span>" in text
    assert 'data-target="flow-register_user"' in text
    assert 'data-group="Deployment"' not in text
    assert "Deployment Configuration" not in text
    assert "Runtime Containers" in text
    assert 'data-environment-trigger aria-label="Deployment environment"' in text
    assert 'role="listbox" data-environment-menu hidden' in text
    assert 'data-environment-option="development"' in text
    assert "runtime-container-card" in text
    assert "runtime-deployment-panel" in text
    assert "annotation-filter" in text
    assert "data-filter-values" in text
    assert 'data-filter-value="interface"' in text
    assert 'data-filter-value="payload"' in text
    assert 'data-filter-value="account_router"' in text
    assert "Raw Entity Payload" not in text
    assert "Raw Persistence Payload" not in text
    assert "Security Surface" in text
    assert "Security constraints collected across system, runtime, data, and persistence." in text
    assert "runtime-container-stats" not in text
    assert "Extracted data shapes" not in text
    assert "Extracted operations" not in text
    assert "chip-storage" in text
    assert "chip-table" in text
    assert ">relational<" in text
    assert ">notes_db<" in text
    assert "<summary>Components (3)</summary>" in text
    frontend_section = text[text.index('id="container-frontend_ui"') : text.index('id="container-backend_api"')]
    assert "notes_screen --&gt; note_card" in frontend_section
    assert "frontend_ui --&gt; backend_api" in text
    assert "backend_api --&gt; frontend_ui" in text
    assert "backend_api --&gt; frontend_ui" in text
    assert "No validation findings." in text
    backend_section = text[text.index('id="container-backend_api"') : text.index('id="container-notes_db"')]
    assert backend_section.index("account_repository") < backend_section.index("account_router") < backend_section.index("account_service")
    assert backend_section.index("note_repository") < backend_section.index("note_service") < backend_section.index("notes_router")
    assert "Forge audit written to" in capsys.readouterr().out


def test_v4_live_audit_rerenders_mermaid_chart_from_current_schema(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    initial_html = render_live_audit_html(copied_root)
    initial_section = initial_html[initial_html.index('id="flow-register_user"') : initial_html.index('id="flow-sign_in_user"')]
    assert "frontend_ui --&gt; backend_api" in initial_section
    assert "backend_api --&gt; notes_db" in initial_section
    assert "frontend_ui --&gt; notes_db" not in initial_section

    containers_path = copied_root / "forge" / "containers.yaml"
    payload = yaml.safe_load(containers_path.read_text(encoding="utf-8"))
    payload["container_flows"][0]["steps"][1]["container"] = "notes_db"
    containers_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    updated_html = render_live_audit_html(copied_root)
    updated_section = updated_html[updated_html.index('id="flow-register_user"') : updated_html.index('id="flow-sign_in_user"')]
    assert "frontend_ui --&gt; backend_api" not in updated_section
    assert "frontend_ui --&gt; notes_db" in updated_section


def test_init_scaffolds_v4_project(tmp_path: Path, capsys) -> None:
    root = tmp_path / "demo-v4"

    assert main(["init", "--root", str(root), "--name", "Demo V4", "--id", "demo_v4", "--no-animation"]) == 0

    forge_root = root / "forge"
    assert (forge_root / "system.yaml").exists()
    assert (forge_root / "containers.yaml").exists()
    assert (forge_root / "entities.yaml").exists()
    assert (forge_root / "decisions.yaml").exists()
    assert (forge_root / "crawler.yaml").exists()
    assert (root / "business-plan.md").exists()
    assert (forge_root / "FRAMEWORK_V4.md").exists()
    assert (forge_root / "SCHEMA_REFERENCE_V4.md").exists()
    assert (forge_root / "skills" / "forge-business" / "SKILL.md").exists()
    assert (forge_root / "skills" / "forge-schema" / "SKILL.md").exists()
    assert (forge_root / "skills" / "forge-hydrate" / "SKILL.md").exists()
    skill_text = (forge_root / "skills" / "forge-schema" / "SKILL.md").read_text(encoding="utf-8")
    assert "forge/FRAMEWORK_V4.md" in skill_text
    assert "forge/SCHEMA_REFERENCE_V4.md" in skill_text
    capsys.readouterr()
    assert main(["crawl", "--project-dir", str(root)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "forge.extracted_model"
    assert payload["system"]["id"] == "demo_v4"
    assert payload["decisions"] == []


def test_default_comment_profiles_cover_common_language_prefixes(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    examples = {
        "worker.go": "//",
        "lib.rs": "//",
        "Handler.java": "//",
        "Program.cs": "//",
        "View.swift": "//",
        "Main.kt": "//",
        "script.rb": "#",
        "task.sh": "#",
        "query.sql": "--",
    }
    for filename, prefix in examples.items():
        (copied_root / "apps" / "frontend" / "src" / filename).write_text(
            "\n".join(
                [
                    f"{prefix} @forge:component",
                    f"{prefix} id: component_{filename.split('.')[0].lower()}",
                    f"{prefix} role: utility",
                    f"{prefix} description: Common language fixture.",
                    f"{prefix} data_shapes: []",
                    f"{prefix} responsibilities:",
                    f"{prefix}   - Prove default prefix parsing.",
                ]
            ),
            encoding="utf-8",
        )

    payload = crawl_project(copied_root).to_dict()

    assert payload["summary"]["components"] == 12 + len(examples)
    assert payload["warnings"]["skipped_file_types"] == []


def _copy_v4_example(tmp_path: Path) -> Path:
    copied_root = tmp_path / "forge_minimal_web_app"
    shutil.copytree(V4_EXAMPLE_ROOT, copied_root)
    return copied_root
