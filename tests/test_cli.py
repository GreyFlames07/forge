"""End-to-end tests for the CLI dispatcher (context / list / inspect / find)."""

import io
from contextlib import redirect_stderr, redirect_stdout
from importlib import metadata
from pathlib import Path

import pytest

from cli import forge as forge_mod
from cli.forge import main

EXAMPLE = str(Path(__file__).resolve().parent.parent / "example" / "spec")

SHORT_LINK = "linkhub.shortener.links.link_manager.short_link"
SHORT_CODE = "linkhub.shortener.types.ShortCode"


def _run(args: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(args)
    return rc, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------

def test_version_flag_prints_version_and_exits_0():
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err), pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    assert out.getvalue().startswith("forge ")
    assert err.getvalue() == ""


def test_version_string_prefers_ai_forge_cli_distribution(monkeypatch):
    versions = {
        "ai-forge-cli": "0.1.8",
        "forge-ai-cli": "0.1.1",
    }

    def fake_version(name: str) -> str:
        if name in versions:
            return versions[name]
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(forge_mod.metadata, "version", fake_version)
    assert forge_mod._version_string() == "0.1.8"


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------

def test_context_element_rc0():
    rc, out, _ = _run(["context", SHORT_LINK, "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "FORGE CONTEXT BUNDLE" in out
    assert SHORT_LINK in out


def test_context_unknown_id_exits_1():
    rc, _, err = _run(["context", "linkhub.shortener.links.link_manager.nonexistent", "--spec-dir", EXAMPLE])
    assert rc == 1
    assert "error:" in err.lower() or "unknown" in err.lower()


def test_context_non_bundleable_exits_1():
    rc, _, err = _run(["context", SHORT_CODE, "--spec-dir", EXAMPLE])
    assert rc == 1
    assert "error:" in err.lower() or "only" in err.lower()


def test_context_format_markdown():
    rc, out, _ = _run(["context", SHORT_LINK, "--spec-dir", EXAMPLE, "--format", "markdown"])
    assert rc == 0
    assert "#" in out  # markdown headers


def test_context_format_json():
    rc, out, _ = _run(["context", SHORT_LINK, "--spec-dir", EXAMPLE, "--format", "json"])
    assert rc == 0
    stripped = out.lstrip()
    assert stripped.startswith("{")
    assert '"target"' in out


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def test_list_default_groups_by_kind():
    rc, out, _ = _run(["list", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "# element" in out
    assert SHORT_LINK in out


def test_list_kind_filter_element():
    rc, out, _ = _run(["list", "--kind", "element", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert SHORT_LINK in out
    assert "# module" not in out


def test_list_kind_filter_module():
    rc, out, _ = _run(["list", "--kind", "module", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "linkhub.shortener.links.link_manager" in out
    assert "# element" not in out


def test_list_ids_only():
    rc, out, _ = _run(["list", "--kind", "element", "--ids-only", "--spec-dir", EXAMPLE])
    assert rc == 0
    lines = [line for line in out.splitlines() if line.strip()]
    for line in lines:
        assert not line.startswith("#")
        assert not line.startswith(" ")


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------

def test_inspect_element():
    rc, out, _ = _run(["inspect", SHORT_LINK, "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "kind: element" in out
    assert "element_kind: aggregate" in out
    assert "bundleable: true" in out


def test_inspect_type():
    rc, out, _ = _run(["inspect", SHORT_CODE, "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "kind: type" in out
    assert "bundleable: false" in out


def test_inspect_module():
    rc, out, _ = _run(["inspect", "linkhub.shortener.links.link_manager", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "kind: module" in out


def test_inspect_unknown_id():
    rc, _, err = _run(["inspect", "linkhub.shortener.typo_here", "--spec-dir", EXAMPLE])
    assert rc == 1
    assert "unknown" in err.lower()
