from __future__ import annotations

from pathlib import Path

import pytest
import yaml
import json

from cli.forge import main


def test_init_scaffolds_project(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    home = tmp_path / "home"
    home.mkdir()
    (home / ".copilot").mkdir()
    import os
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        exit_code = main(["init", "--root", str(root), "--profile", "cli-tool", "--name", "Demo CLI", "--id", "demo_cli"])
        assert exit_code == 0
        assert (root / "forge" / "system.yaml").exists()
        assert (root / "forge" / "workbench" / "status.yaml").exists()
        assert (root / "apps" / "cli").exists()
        assert (root / "apps" / "cli" / "src" / "main.txt").exists()
        assert (root / "forge" / "units" / "cli.yaml").exists()
        assert (root / ".agents" / "skills" / "forge-spec" / "SKILL.md").exists()
        assert (root / "frameworks" / "spec" / "FRAMEWORK.md").exists()
        assert (root / "docs" / "forge-v2-schema.md").exists()
        assert (root / ".agents" / "skills" / "forge-spec" / "SKILL.md").read_text(encoding="utf-8") == (
            Path("skills") / "forge-spec" / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert (home / ".claude" / "skills" / "forge-spec").is_symlink()
        assert (home / ".codex" / "skills" / "forge-spec").is_symlink()
        assert (home / ".agents" / "skills" / "forge-spec").is_symlink()
        assert (home / ".copilot" / "skills" / "forge-spec").is_symlink()
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home


def test_list_without_project_fails_cleanly(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["list"]) == 1
    output = capsys.readouterr().out
    assert "Could not find a Forge project" in output


def test_list_renders_sections(sample_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(sample_project)
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert "units:" in output
    assert "operations:" in output


def test_list_supports_json_and_kind_alias(sample_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(sample_project)
    assert main(["list", "--kind", "operations", "--format", "json"]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload[0]["id"] == "get_health"


def test_context_renders(sample_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(sample_project)
    assert main(["context", "get_health", "--format", "markdown"]) == 0
    output = capsys.readouterr().out
    assert "Context: get_health" in output
    assert "likely implementation paths:" in output


def test_context_yaml_includes_multi_type_keys(sample_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(sample_project)
    assert main(["context", "get_health"]) == 0
    output = capsys.readouterr().out
    assert "# Context: get_health" in output
    assert "# Kind: operation" in output
    payload = yaml.safe_load(output)
    assert "input_types" in payload
    assert "output_types" in payload
    assert payload["output_types"][0]["id"] == "HealthResponse"
    assert "workbench" in payload
    assert "implementation_hints" in payload
    assert "verification_refs" in payload
    assert "contract_refs" in payload
    assert "runtime_refs" in payload


def test_context_unit_expands_from_unit_collection(sample_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(sample_project)
    assert main(["context", "api"]) == 0
    output = capsys.readouterr().out
    payload = yaml.safe_load(output)
    assert payload["target"]["kind"] == "service"
    assert payload["surfaces"][0]["id"] == "health_http"
    assert payload["operations"][0]["id"] == "get_health"
    assert payload["startup_checks"][0]["id"] == "api_health"
    assert payload["implementation_hints"][0].endswith("apps/api/src/main.txt")


def test_context_relatedness_uses_real_id_references(sample_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(sample_project)
    assert main(["context", "api"]) == 0
    output = capsys.readouterr().out
    payload = yaml.safe_load(output)
    assert "app" not in payload["related"]["referenced_by"]
    assert "demo" not in payload["related"]["referenced_by"]


def test_context_unknown_id_suggests_matches(sample_project: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(sample_project)
    assert main(["context", "get_healt"]) == 1
    output = capsys.readouterr().out
    assert "Unknown id: get_healt" in output
    assert "Did you mean:" in output
    assert "get_health" in output


def test_graph_writes_interactive_html(sample_project: Path, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(sample_project)
    output = tmp_path / "graph.html"
    assert main(["graph", "--forge-dir", str(sample_project / "forge"), "--output", str(output), "--no-open"]) == 0
    html = output.read_text(encoding="utf-8")
    assert "cytoscape.min.js" in html
    assert "Node Kinds" in html
    assert "Relationship Families" in html
    assert 'data-preset="runtime"' in html
    assert "verification.startup.api_health" in html
    assert '"layers": {' in html
    assert '"surfaces": [' in html
    assert '"operations": [' in html
    assert 'id="zoom-in"' in html
    assert 'id="zoom-reset"' in html
    assert 'Bootstrap<br/><small>bootstrap</small>' not in html


def test_help_exposes_expected_commands(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "{init,graph,context,list}" in output
