from __future__ import annotations

from pathlib import Path

from cli.forge import main


REPO_ROOT = Path(__file__).resolve().parents[1]

def test_full_stack_example_list_and_context(monkeypatch, capsys) -> None:
    root = REPO_ROOT / "examples" / "minimal-full-stack"
    monkeypatch.chdir(root)
    assert main(["list", "operations", "--forge-dir", str(root / "forge")]) == 0
    assert "load_dashboard" in capsys.readouterr().out
    assert main(["context", "load_dashboard", "--forge-dir", str(root / "forge"), "--format", "markdown"]) == 0
    output = capsys.readouterr().out
    assert "Context: load_dashboard" in output


def test_examples_graph_and_list() -> None:
    for name in ("minimal-full-stack", "minimal-cli", "minimal-worker-service"):
        forge_dir = REPO_ROOT / "examples" / name / "forge"
        assert main(["list", "--forge-dir", str(forge_dir)]) == 0


def test_example_skills_match_root_skills() -> None:
    root_skill = (REPO_ROOT / "skills" / "forge-spec" / "SKILL.md").read_text(encoding="utf-8")
    for name in ("minimal-full-stack", "minimal-cli", "minimal-worker-service"):
        example_skill = (
            REPO_ROOT / "examples" / name / ".agents" / "skills" / "forge-spec" / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert example_skill == root_skill
