"""Smoke tests for `forge init`."""

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


def test_init_creates_spec_with_framework_and_conception():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["init", "--no-banner"])
        assert rc == 0, f"init exited {rc}: {err}"

        spec = td_path / "spec"
        assert spec.is_dir()
        assert (spec / "framework.yaml").is_file()
        assert (spec / "conception.yaml").is_file()

        # No L-layer subdirectories — those are v1 artifacts
        for unwanted in ("L2_modules", "L3_atoms", "L4_flows", "L5_operations"):
            assert not (spec / unwanted).exists(), f"unexpected dir: {unwanted}"


def test_init_conception_stub_has_required_fields():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            _run(["init", "--no-banner"])
        import yaml
        data = yaml.safe_load((td_path / "spec" / "conception.yaml").read_text())
        assert "id" in data
        assert "type" in data
        assert data["type"] == "conception"


def test_init_framework_yaml_has_enums():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            _run(["init", "--no-banner"])
        import yaml
        fw = yaml.safe_load((td_path / "spec" / "framework.yaml").read_text())
        assert "enums" in fw or "scalars" in fw  # at least one framework section


def test_init_refuses_over_existing_project():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        spec = td_path / "spec"
        spec.mkdir(parents=True)
        (spec / "conception.yaml").write_text("id: existing\n")

        with chdir(td_path):
            rc, out, err = _run(["init", "--no-banner"])
        assert rc == 1
        assert "existing forge project" in err


def test_init_force_overwrites_framework():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        spec = td_path / "spec"
        spec.mkdir(parents=True)
        (spec / "framework.yaml").write_text("stale: true\n")
        (spec / "conception.yaml").write_text("id: my-conception\ntype: conception\n")

        with chdir(td_path):
            rc, out, err = _run(["init", "--force", "--no-banner"])
        assert rc == 0
        # framework.yaml should now contain real content (not the stale stub)
        fw_text = (spec / "framework.yaml").read_text()
        assert "stale: true" not in fw_text


def test_init_custom_spec_subdir():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["init", "--spec-subdir", "myspec", "--no-banner"])
        assert rc == 0
        assert (td_path / "myspec").is_dir()
        assert (td_path / "myspec" / "framework.yaml").is_file()
        # Default location NOT created
        assert not (td_path / "spec").exists()


def test_init_no_banner_skips_animation():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with chdir(td_path):
            rc, out, err = _run(["init", "--no-banner"])
        assert rc == 0
        # Should still print progress info even without banner
        assert "framework.yaml" in out or "conception.yaml" in out
