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


def test_update_refuses_without_existing_project():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["update"])
        assert rc == 1
        assert "no forge project" in err.lower() or "no Forge project" in err


def test_update_refuses_when_spec_dir_missing():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["update", "--spec-dir", "nonexistent"])
        assert rc == 1
        assert "no Forge project" in err or "no forge project" in err.lower()


def test_update_refreshes_framework_yaml():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            # Bootstrap a project
            rc, out, err = _run(["init", "--no-banner"])
            assert rc == 0, f"init failed: {err}"

            # Corrupt the framework.yaml
            fw = td_path / "spec" / "framework.yaml"
            fw.write_text("stale: content\n")

            # Update with --force should restore it
            rc, out, err = _run(["update", "--force"])

        assert rc == 0, f"update exited {rc}: {err}"
        fw_text = (td_path / "spec" / "framework.yaml").read_text()
        assert "stale: content" not in fw_text


def test_update_does_not_overwrite_without_force():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, _, err = _run(["init", "--no-banner"])
            assert rc == 0

            fw = td_path / "spec" / "framework.yaml"
            fw.write_text("custom: preserved\n")

            rc, out, _ = _run(["update"])

        assert rc == 0
        assert (td_path / "spec" / "framework.yaml").read_text() == "custom: preserved\n"


def test_update_respects_custom_spec_dir():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, _, err = _run(["init", "--spec-subdir", "myspec", "--no-banner"])
            assert rc == 0

            fw = td_path / "myspec" / "framework.yaml"
            original = fw.read_text()
            fw.write_text("stale: true\n")

            rc, out, err = _run(["update", "--spec-dir", "myspec", "--force"])

        assert rc == 0, f"update failed: {err}"
        updated = (td_path / "myspec" / "framework.yaml").read_text()
        assert "stale: true" not in updated


def test_update_prints_validate_hint():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            _run(["init", "--no-banner"])
            rc, out, err = _run(["update"])
        assert rc == 0
        assert "validate" in out.lower()
