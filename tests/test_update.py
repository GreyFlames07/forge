"""Smoke tests for `forge update`."""

import io
import tempfile
from contextlib import chdir, redirect_stderr, redirect_stdout
from pathlib import Path

from cli.forge import main


def _run(args: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(args)
    return rc, out.getvalue(), err.getvalue()


def test_update_refreshes_managed_assets_and_prints_audit_hint():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["init"])
            assert rc == 0, f"init exited {rc}: {err}"

            template = td_path / ".forge" / "templates" / "L0_registry.schema.md"
            template.unlink()
            template.write_text("stale template\n")

            skill_link = td_path / ".claude" / "skills" / "forge-atom"
            skill_link.unlink()

            gitkeep = td_path / ".forge" / "L4_flows" / ".gitkeep"
            gitkeep.unlink()

            rc, out, err = _run(["update"])

        assert rc == 0, f"update exited {rc}: {err}"
        assert template.is_symlink()
        assert template.is_file()
        assert skill_link.is_symlink()
        assert (skill_link / "SKILL.md").is_file()
        assert gitkeep.is_file()
        assert "/forge-audit" in out
        assert "Audit the specs before implementation" in out


def test_update_refuses_without_existing_project():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["update"])
        assert rc == 1
        assert "no forge project detected" in err


def test_update_respects_custom_spec_subdir():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["init", "--spec-subdir", "specs"])
            assert rc == 0, f"init exited {rc}: {err}"

            template = td_path / "specs" / "templates" / "L1_conventions.schema.md"
            template.unlink()

            rc, out, err = _run(["update", "--spec-subdir", "specs"])

        assert rc == 0, f"update exited {rc}: {err}"
        assert template.is_symlink()
        assert template.is_file()
