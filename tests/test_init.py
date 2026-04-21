"""Smoke tests for `forge init`."""

import io
import os
import tempfile
from contextlib import chdir, redirect_stderr, redirect_stdout
from pathlib import Path

from cli.commands import init as init_cmd
from cli.forge import main


def _run(args: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(args)
    return rc, out.getvalue(), err.getvalue()


def test_init_creates_spec_structure_and_symlinks():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["init"])
        assert rc == 0, f"init exited {rc}: {err}"

        spec = td_path / ".forge"
        assert spec.is_dir()
        for sub in ("L2_modules", "L2_policies", "L3_atoms",
                    "L3_artifacts", "L4_flows", "L4_journeys"):
            assert (spec / sub).is_dir(), f"missing {sub}"
            assert (spec / sub / ".gitkeep").is_file()

        # Schema template symlinks at .forge/templates/
        tmpl = spec / "templates"
        assert tmpl.is_dir()
        expected_templates = {
            "L0_registry.schema.md", "L0_registry.guide.md",
            "L1_conventions.schema.md", "L1_conventions.guide.md",
            "L2_architecture.schema.md", "L2_architecture.guide.md",
            "L3_behavior.schema.md", "L3_behavior.guide.md",
            "L4_flows.schema.md", "L4_flows.guide.md",
            "L5_operations.schema.md", "L5_operations.guide.md",
        }
        present = {p.name for p in tmpl.iterdir()}
        assert expected_templates == present, \
            f"template mismatch. Missing: {expected_templates - present}. Extra: {present - expected_templates}"
        # Each template is a symlink pointing at a real .md file
        for name in expected_templates:
            link = tmpl / name
            assert link.is_symlink(), f"{name} is not a symlink"
            assert link.is_file(), f"{name} symlink target is broken"

        # Symlinks created for all three discovery paths (Claude Code, Codex, agentskills.io).
        claude = td_path / ".claude" / "skills"
        codex  = td_path / ".codex"  / "skills"
        agents = td_path / ".agents" / "skills"
        assert claude.is_dir()
        assert codex.is_dir()
        assert agents.is_dir()

        for skill in init_cmd.SKILL_NAMES:
            assert (claude / skill).is_symlink(), f"missing claude link for {skill}"
            assert (codex  / skill).is_symlink(), f"missing codex link for {skill}"
            assert (agents / skill).is_symlink(), f"missing agents link for {skill}"
            # Symlink targets resolve to a directory with a SKILL.md
            assert ((claude / skill) / "SKILL.md").is_file()
            assert ((codex  / skill) / "SKILL.md").is_file()
            assert ((agents / skill) / "SKILL.md").is_file()


def test_init_refuses_over_existing_project():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        spec = td_path / ".forge"
        spec.mkdir(parents=True)
        (spec / "L0_registry.yaml").write_text("existing: true\n")

        with chdir(td_path):
            rc, out, err = _run(["init"])
        assert rc == 1
        assert "existing forge project" in err


def test_init_force_overwrites():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        spec = td_path / ".forge"
        spec.mkdir(parents=True)
        (spec / "L0_registry.yaml").write_text("existing: true\n")

        with chdir(td_path):
            rc, out, err = _run(["init", "--force"])
        assert rc == 0
        # Existing spec file preserved (init does not overwrite spec content)
        assert (spec / "L0_registry.yaml").read_text() == "existing: true\n"


def test_init_skip_skills():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["init", "--skip-skills"])
        assert rc == 0
        assert (td_path / ".forge").is_dir()
        # Templates still symlinked even when --skip-skills
        assert (td_path / ".forge" / "templates").is_dir()
        assert not (td_path / ".claude" / "skills").exists()
        assert not (td_path / ".codex"  / "skills").exists()
        assert not (td_path / ".agents" / "skills").exists()


def test_init_custom_spec_subdir():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["init", "--spec-subdir", "specs"])
        assert rc == 0
        assert (td_path / "specs").is_dir()
        assert (td_path / "specs" / "L2_modules").is_dir()
        assert (td_path / "specs" / "templates").is_dir()
        # Default location NOT created.
        assert not (td_path / ".forge").exists()


def test_resolve_forge_sources_uses_cached_repo_when_local_skills_missing(monkeypatch, tmp_path):
    fake_cli = tmp_path / "venv" / "lib" / "python3.13" / "site-packages" / "cli" / "__init__.py"
    fake_cli.parent.mkdir(parents=True)
    fake_cli.write_text("# fake cli package\n")

    cached_repo = tmp_path / "cache" / "repo"
    cached_skills = cached_repo / ".agents" / "skills"
    cached_skills.mkdir(parents=True)
    (cached_repo / "src" / "templates").mkdir(parents=True)

    monkeypatch.setattr(init_cmd.cli, "__file__", str(fake_cli))
    monkeypatch.setattr(init_cmd, "_cached_forge_repo", lambda: cached_repo)

    repo, skills = init_cmd._resolve_forge_sources()
    assert repo == cached_repo
    assert skills == cached_skills


def test_installed_cli_version_prefers_ai_forge_cli_distribution(monkeypatch):
    versions = {
        "ai-forge-cli": "0.1.4",
        "forge-ai-cli": "0.1.1",
    }

    def fake_version(name: str) -> str:
        if name in versions:
            return versions[name]
        raise init_cmd.metadata.PackageNotFoundError

    monkeypatch.setattr(init_cmd.metadata, "version", fake_version)
    assert init_cmd._installed_cli_version() == "0.1.4"
