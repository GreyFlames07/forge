from __future__ import annotations

import importlib.resources
import json
import shutil
import socket
import tomllib
from pathlib import Path

import yaml

from cli import __version__
from cli.commands import audit as audit_command
from cli.commands.audit import _edge_label, _state_machine_partitions, render_live_audit_html
from cli.forge import main

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = REPO_ROOT / "examples" / "forge_minimal_web_app"


def test_package_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert __version__ == pyproject["project"]["version"]


def test_container_flow_context_json(capsys) -> None:
    assert main(["context", "--project-dir", str(EXAMPLE_ROOT), "--flow", "create_note"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"]["type"] == "container_flow"
    assert payload["target"]["id"] == "create_note"
    assert payload["artifacts"]["container_flow"]["id"] == "create_note"
    assert {container["id"] for container in payload["artifacts"]["containers"]} >= {"frontend_ui", "backend_api"}


def test_container_context_yaml(capsys) -> None:
    assert main(
        [
            "context",
            "--project-dir",
            str(EXAMPLE_ROOT),
            "--container",
            "backend_api",
            "--format",
            "yaml",
        ]
    ) == 0
    output = capsys.readouterr().out
    assert "# Context: backend_api" in output
    payload = yaml.safe_load("\n".join(line for line in output.splitlines() if not line.startswith("# ")))
    assert payload["artifacts"]["container"]["id"] == "backend_api"


def test_component_context_json(capsys) -> None:
    assert main(
        [
            "context",
            "--project-dir",
            str(EXAMPLE_ROOT),
            "--component",
            "account_screen",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"]["type"] == "component"
    assert payload["artifacts"]["component"]["id"] == "account_screen"
    assert payload["artifacts"]["container"]["id"] == "frontend_ui"


def test_flow_context_markdown(capsys) -> None:
    assert main(
        [
            "context",
            "--project-dir",
            str(EXAMPLE_ROOT),
            "--flow",
            "create_note",
            "--format",
            "md",
        ]
    ) == 0
    output = capsys.readouterr().out
    assert "Context: create_note" in output
    assert "container_flow:" in output


def test_init_scaffolds_traversable_repo(tmp_path: Path, capsys) -> None:
    root = tmp_path / "demo"
    assert main(["init", "--root", str(root), "--name", "Demo System", "--id", "demo_system", "--no-animation"]) == 0
    forge_root = root / "forge"
    output = capsys.readouterr().out
    assert "Forge initialized at" in output
    assert "forge workspace:" in output
    assert "Start With Skills" in output
    assert "Use Forge In This Order" in output
    assert "How To Get The Most Out Of The Framework" in output
    assert "forge/skills/forge-schema/SKILL.md" in output
    assert "forge/skills/forge-review/SKILL.md" in output
    assert "forge/skills/forge-security/SKILL.md" in output
    assert "Run `forge-review` and `forge-security` before building." in output
    assert "the CLI supports the active skill" in output
    assert "CLI Support Workflow" in output
    assert "forge audit --project-dir" in output
    assert (forge_root / "system.yaml").exists()
    assert (forge_root / "containers.yaml").exists()
    assert (forge_root / "entities.yaml").exists()
    assert (forge_root / "decisions.yaml").exists()
    assert (forge_root / "crawler.yaml").exists()
    assert (root / "business-plan.md").exists()
    assert "Business Plan: Demo System" in (root / "business-plan.md").read_text(encoding="utf-8")
    assert (forge_root / "SCHEMA_REFERENCE_V4.md").exists()
    assert (forge_root / "FRAMEWORK_V4.md").exists()
    assert (forge_root / "USING_FORGE.md").exists()
    assert (forge_root / "skills" / "forge-business" / "SKILL.md").exists()
    assert (forge_root / "skills" / "forge-schema" / "SKILL.md").exists()
    assert (forge_root / "skills" / "forge-hydrate" / "SKILL.md").exists()
    assert "dist/" in (root / ".gitignore").read_text(encoding="utf-8")
    assert "*.egg-info/" in (root / ".gitignore").read_text(encoding="utf-8")
    codex_skill = root / ".codex" / "skills" / "forge-build"
    assert codex_skill.is_dir()
    assert not codex_skill.is_symlink()
    assert (codex_skill / "SKILL.md").exists()
    assert (codex_skill / "agents" / "openai.yaml").exists()
    assert not (codex_skill / "coding_agent_skills_reference").exists()
    surfaced_skill = (codex_skill / "SKILL.md").read_text(encoding="utf-8")
    assert "../../../forge/USING_FORGE.md" in surfaced_skill
    assert "../forge-schema/SKILL.md" in surfaced_skill
    assert (root / ".claude" / "skills" / "forge-business" / "SKILL.md").exists()
    assert (root / ".claude" / "skills" / "forge-schema" / "SKILL.md").exists()
    assert (root / ".claude" / "skills" / "forge-hydrate" / "SKILL.md").exists()
    assert (root / ".agents" / "skills" / "forge-review" / "SKILL.md").exists()
    rewritten_skill = (forge_root / "skills" / "forge-schema" / "SKILL.md").read_text(encoding="utf-8")
    assert "../../SCHEMA_REFERENCE_V4.md" in rewritten_skill
    assert "../../USING_FORGE.md" in rewritten_skill
    usage_doc = (forge_root / "USING_FORGE.md").read_text(encoding="utf-8")
    assert "Forge is **skills-first**." in usage_doc
    assert "Use Forge In This Order" in usage_doc
    assert "Skill Roles" in usage_doc
    assert "forge-business" in usage_doc
    assert "forge-hydrate" in usage_doc
    assert main(["context", "--project-dir", str(root), "--system", "--format", "json"]) == 0
    context_output = capsys.readouterr().out
    payload = json.loads(context_output)
    assert payload["target"]["type"] == "system"
    assert payload["target"]["id"] == "demo_system"
    capsys.readouterr()
    assert main(["crawl", "--project-dir", str(root), "--format", "json"]) == 0
    crawl_payload = json.loads(capsys.readouterr().out)
    assert crawl_payload["decisions"] == []


def test_packaged_init_docs_exist() -> None:
    package_resources = importlib.resources.files("cli").joinpath("resources")
    assert package_resources.joinpath("SCHEMA_REFERENCE_V4.md").is_file()
    assert package_resources.joinpath("FRAMEWORK_V4.md").is_file()
    assert package_resources.joinpath("skills", "forge-schema", "SKILL.md").is_file()
    assert package_resources.joinpath("skills", "forge-build", "SKILL.md").is_file()


def test_packaged_skill_frontmatter_is_valid_yaml() -> None:
    package_skills = importlib.resources.files("cli").joinpath("resources", "skills")
    for skill_file in package_skills.glob("forge-*/SKILL.md"):
        text = skill_file.read_text(encoding="utf-8")
        _, frontmatter, _ = text.split("---", 2)
        payload = yaml.safe_load(frontmatter)
        assert isinstance(payload, dict), f"{skill_file} frontmatter must parse to a mapping"
        assert payload.get("name"), f"{skill_file} frontmatter must include a name"
        assert payload.get("description"), f"{skill_file} frontmatter must include a description"


def test_packaged_skill_docs_match_source_skill_docs() -> None:
    source_skills = REPO_ROOT / "skills"
    package_skills = REPO_ROOT / "src" / "cli" / "resources" / "skills"
    source_skill_docs = sorted(source_skills.glob("forge-*/SKILL.md"))
    package_skill_docs = sorted(package_skills.glob("forge-*/SKILL.md"))

    assert [path.parent.name for path in package_skill_docs] == [path.parent.name for path in source_skill_docs]

    for source_skill_doc in source_skill_docs:
        package_skill_doc = package_skills / source_skill_doc.parent.name / "SKILL.md"
        assert package_skill_doc.read_text(encoding="utf-8") == source_skill_doc.read_text(encoding="utf-8")


def test_packaged_framework_docs_match_source_docs() -> None:
    for filename in ("FRAMEWORK_V4.md", "SCHEMA_REFERENCE_V4.md"):
        source_doc = REPO_ROOT / filename
        package_doc = REPO_ROOT / "src" / "cli" / "resources" / filename
        assert package_doc.read_text(encoding="utf-8") == source_doc.read_text(encoding="utf-8")


def test_audit_generates_html(tmp_path: Path, capsys) -> None:
    output = tmp_path / "forge-audit.html"
    assert main(
        [
            "audit",
            "--project-dir",
            str(EXAMPLE_ROOT),
            "--artifact",
            "--output",
            str(output),
            "--no-open",
        ]
    ) == 0
    text = output.read_text(encoding="utf-8")
    assert "Forge Audit" in text
    assert "class=\"subnav\"" in text
    assert 'id="overview"' not in text
    assert '>Overview<' not in text
    assert "system-overview" in text
    assert "runtime-overview" in text
    assert "data-overview" in text
    assert 'data-group="Deployment"' not in text
    assert "container-backend_api" in text
    assert 'id="flow-create_note"' in text
    assert "validate_create_note" in text
    assert "&quot;session_token&quot;: &quot;string&quot;" in text
    assert "&quot;status&quot;: &quot;enum[active, archived]&quot;" in text
    assert 'id="entity-note"' in text
    assert "Lifecycle" in text
    assert "Data Shapes" in text
    assert "Persistence" in text


def test_audit_no_open_suppresses_live_browser(monkeypatch) -> None:
    calls: list[bool] = []

    def fake_serve(_root: Path, *, open_browser: bool, port: int = audit_command.DEFAULT_AUDIT_PORT) -> None:
        assert port == audit_command.DEFAULT_AUDIT_PORT
        calls.append(open_browser)

    def fail_open(_path: str | Path) -> None:
        raise AssertionError("_open_file should not be called with --no-open")

    monkeypatch.setattr(audit_command, "_serve_audit", fake_serve)
    monkeypatch.setattr(audit_command, "_open_file", fail_open)

    assert main(["audit", "--project-dir", str(EXAMPLE_ROOT), "--no-open"]) == 0
    assert calls == [False]


def test_audit_headless_suppresses_live_browser(monkeypatch) -> None:
    calls: list[bool] = []

    def fake_serve(_root: Path, *, open_browser: bool, port: int = audit_command.DEFAULT_AUDIT_PORT) -> None:
        assert port == audit_command.DEFAULT_AUDIT_PORT
        calls.append(open_browser)

    def fail_open(_path: str | Path) -> None:
        raise AssertionError("_open_file should not be called with --headless")

    monkeypatch.setattr(audit_command, "_serve_audit", fake_serve)
    monkeypatch.setattr(audit_command, "_open_file", fail_open)

    assert main(["audit", "--project-dir", str(EXAMPLE_ROOT), "--headless"]) == 0
    assert calls == [False]


def test_audit_live_server_reuses_occupied_port(monkeypatch, capsys) -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]

    def fail_open(_path: str | Path) -> None:
        raise AssertionError("_open_file should not be called when the audit port is already occupied")

    monkeypatch.setattr(audit_command, "_open_file", fail_open)
    try:
        audit_command._serve_audit(EXAMPLE_ROOT, open_browser=True, port=port)
    finally:
        listener.close()

    assert f"Forge audit live server already running at http://127.0.0.1:{port}" in capsys.readouterr().out


def test_audit_headless_suppresses_artifact_open(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "forge-audit.html"

    def fail_open(_path: str | Path) -> None:
        raise AssertionError("_open_file should not be called with --headless")

    monkeypatch.setattr(audit_command, "_open_file", fail_open)

    assert main(["audit", "--project-dir", str(EXAMPLE_ROOT), "--artifact", "--output", str(output), "--headless"]) == 0
    assert output.exists()


def test_operation_context_json(capsys) -> None:
    assert main(["context", "--project-dir", str(EXAMPLE_ROOT), "--operation", "validate_create_note"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"]["type"] == "operation"
    assert payload["target"]["id"] == "validate_create_note"
    assert payload["artifacts"]["operation"]["payload"]["input"] == "ref[create_note_command]"
    assert payload["artifacts"]["operation"]["payload"]["returns"] == "ref[pending_note_record]"
    assert payload["artifacts"]["container"]["id"] == "backend_api"


def test_context_requires_explicit_scope(capsys) -> None:
    assert main(["context", "--project-dir", str(EXAMPLE_ROOT)]) == 1
    output = capsys.readouterr().out
    assert "No context target selected." in output


def test_crawl_validation_reports_broken_references(tmp_path: Path, capsys) -> None:
    broken_root = tmp_path / "broken-example"
    shutil.copytree(EXAMPLE_ROOT, broken_root)
    containers_path = broken_root / "forge" / "containers.yaml"
    containers_path.write_text(
        containers_path.read_text(encoding="utf-8").replace("notes_db", "missing_notes_db", 1),
        encoding="utf-8",
    )
    assert main(["crawl", "--project-dir", str(broken_root), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    unresolved = payload["findings"]["unresolved_references"]
    assert {
        "kind": "container_flow",
        "id": "register_user",
        "field": "step.container",
        "reference": "notes_db",
        "expected_kind": "container",
        "message": "`notes_db` does not resolve to a known container.",
    } in unresolved


def test_component_flow_terminal_outgoing_is_valid_and_rendered(tmp_path: Path) -> None:
    copied_root = tmp_path / "terminal-outgoing-example"
    shutil.copytree(EXAMPLE_ROOT, copied_root)

    container_path = copied_root / "forge" / "containers.yaml"
    container_payload = yaml.safe_load(container_path.read_text(encoding="utf-8"))
    terminal_step = container_payload["container_flows"][2]["steps"][-1]
    terminal_step["output"] = "ref[note_detail_response]"
    container_path.write_text(yaml.safe_dump(container_payload, sort_keys=False), encoding="utf-8")

    html = render_live_audit_html(copied_root)
    assert "Output</span><strong>ref[note_detail_response]" in html


def test_live_audit_rerenders_from_current_schema(tmp_path: Path) -> None:
    copied_root = tmp_path / "example"
    shutil.copytree(EXAMPLE_ROOT, copied_root)

    initial_html = render_live_audit_html(copied_root)
    assert "Shared team note moving from active to archived." in initial_html

    entities_path = copied_root / "forge" / "entities.yaml"
    entities_path.write_text(
        entities_path.read_text(encoding="utf-8").replace(
            "Shared team note moving from active to archived.",
            "Updated live schema description for audit refresh.",
            1,
        ),
        encoding="utf-8",
    )

    updated_html = render_live_audit_html(copied_root)
    assert "Updated live schema description for audit refresh." in updated_html
    assert "Shared team note moving from active to archived." not in updated_html


def test_live_audit_renders_cyclic_persistent_state_machine(tmp_path: Path) -> None:
    copied_root = tmp_path / "cyclic-example"
    shutil.copytree(EXAMPLE_ROOT, copied_root)

    entities_path = copied_root / "forge" / "entities.yaml"
    entities_path.write_text(
        entities_path.read_text(encoding="utf-8").replace(
            "        - from: active\n          to: archived\n          condition: Team member archives the note.\n",
            "        - from: active\n          to: archived\n          condition: Team member archives the note.\n"
            "        - from: archived\n          to: active\n          condition: Team member restores the note.\n",
            1,
        ),
        encoding="utf-8",
    )

    partitions = _state_machine_partitions(
        ["active", "archived"],
        [
            {"from": "active", "to": "archived", "condition": "Team member archives the note."},
            {"from": "archived", "to": "active", "condition": "Team member restores the note."},
        ],
    )
    assert partitions["active"] == 0
    assert partitions["archived"] == 1

    html = render_live_audit_html(copied_root)
    assert "Forge Audit" in html
    assert "Team member restores the note." in html


def test_edge_label_caps_descriptions_to_five_words() -> None:
    assert _edge_label("Order record persisted for reconciliation and downstream fulfillment workflows.") == (
        "Order record persisted for reconciliation"
    )
    assert _edge_label("depends on") == "depends on"
