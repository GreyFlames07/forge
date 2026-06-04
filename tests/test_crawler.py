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
        "components": 12,
        "data_shapes": 32,
        "persistence": 3,
        "operations": 29,
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
    assert payload["summary"]["operations"] == 29
    assert payload["summary"]["validation_findings"] == 0


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
    assert "account_screen" in text
    assert "Flow Diagram: register_user" in text
    assert "team_notes / Flow: register_user" not in text
    assert "Numbered edges correspond to the flow steps below." in text
    assert 'class="flow-step-list"' in text
    assert "mermaid@10" in text
    assert "frontend_ui --&gt;|&quot;1&quot;| backend_api" in text
    assert "Runtime Edge Legend" not in text
    assert "Runtime Topology" in text
    assert "Unique directed connections between runtime containers" in text
    assert "visitor -.-&gt; team_notes" in text
    assert "visitor -.->|&quot;interacts&quot;| team_notes" not in text
    assert 'data-group="Deployment"' not in text
    assert "Deployment Configuration" not in text
    assert "Runtime Containers" in text
    assert 'data-environment-select aria-label="Deployment environment"' in text
    assert "runtime-container-card" in text
    assert "runtime-deployment-panel" in text
    assert "runtime-container-stats" not in text
    assert "Extracted data shapes" not in text
    assert "Extracted operations" not in text
    assert "chip-storage" in text
    assert "chip-table" in text
    assert ">relational<" in text
    assert ">notes_db<" in text
    assert "<summary>Components (3)</summary>" in text
    assert "frontend_ui --&gt; backend_api" in text
    assert "backend_api --&gt; frontend_ui" in text
    assert "backend_api --&gt; notes_db" in text
    assert "No validation findings." in text
    assert "Forge audit written to" in capsys.readouterr().out


def test_v4_live_audit_rerenders_mermaid_chart_from_current_schema(tmp_path: Path) -> None:
    copied_root = _copy_v4_example(tmp_path)
    initial_html = render_live_audit_html(copied_root)
    assert "frontend_ui --&gt;|&quot;1&quot;| backend_api" in initial_html
    assert "frontend_ui --&gt;|&quot;99&quot;| backend_api" not in initial_html

    containers_path = copied_root / "forge" / "containers.yaml"
    payload = yaml.safe_load(containers_path.read_text(encoding="utf-8"))
    payload["container_flows"][0]["steps"][0]["id"] = 99
    containers_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    updated_html = render_live_audit_html(copied_root)
    assert "frontend_ui --&gt;|&quot;99&quot;| backend_api" in updated_html


def test_init_scaffolds_v4_project(tmp_path: Path, capsys) -> None:
    root = tmp_path / "demo-v4"

    assert main(["init", "--root", str(root), "--name", "Demo V4", "--id", "demo_v4", "--schema-version", "v4", "--no-animation"]) == 0

    forge_root = root / "forge"
    assert (forge_root / "system.yaml").exists()
    assert (forge_root / "containers.yaml").exists()
    assert (forge_root / "entities.yaml").exists()
    assert (forge_root / "crawler.yaml").exists()
    assert not (forge_root / "runtime.yaml").exists()
    capsys.readouterr()
    assert main(["crawl", "--project-dir", str(root)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "forge.extracted_model"
    assert payload["system"]["id"] == "demo_v4"


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
