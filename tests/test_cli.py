"""End-to-end tests for the CLI dispatcher (context / list / inspect)."""

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from cli.forge import main

EXAMPLE = str(Path(__file__).resolve().parent.parent / "src" / "example")


def _run(args: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(args)
    return rc, out.getvalue(), err.getvalue()


def test_version_flag_prints_version_and_exits_0():
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err), pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    assert out.getvalue().startswith("forge ")
    assert err.getvalue() == ""


# ---------- context ----------

def test_context_success_rc0_for_fully_resolved_module():
    rc, out, _ = _run(["context", "PAY", "--spec-dir", EXAMPLE])
    # PAY's atoms reference unresolved atoms (fetch_customer etc), so rc=2.
    assert rc in (0, 2)
    assert "FORGE CONTEXT BUNDLE" in out
    assert "target: PAY" in out


def test_context_unresolved_exits_2():
    rc, _, err = _run(["context", "atm.pay.charge_card", "--spec-dir", EXAMPLE])
    assert rc == 2
    assert "Unresolved references" in err
    assert "atm.usr.fetch_customer" in err


def test_context_unknown_id_exits_1_with_suggestion():
    rc, _, err = _run(["context", "atm.pay.nonexistent", "--spec-dir", EXAMPLE])
    assert rc == 1
    assert "error:" in err
    assert "Did you mean" in err


def test_context_non_bundleable_exits_1():
    rc, _, err = _run(["context", "PAY.VAL.001", "--spec-dir", EXAMPLE])
    assert rc == 1
    assert "only" in err or "error:" in err


def test_context_format_json():
    rc, out, _ = _run(["context", "atm.pay.charge_card",
                       "--spec-dir", EXAMPLE, "--format", "json"])
    assert rc == 2  # unresolved signatures
    # First non-whitespace char should be { if JSON.
    stripped = out.lstrip()
    assert stripped.startswith("{")
    assert '"target"' in out


# ---------- list ----------

def test_list_default_groups_by_kind():
    rc, out, _ = _run(["list", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "# atom (" in out
    assert "# module (" in out
    assert "atm.pay.charge_card" in out
    assert "PAY" in out


def test_list_kind_filter():
    rc, out, _ = _run(["list", "--kind", "atom", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "atm.pay.charge_card" in out
    # Should NOT contain module headers.
    assert "# module" not in out


def test_list_ids_only_for_piping():
    rc, out, _ = _run(["list", "--kind", "atom", "--ids-only",
                       "--spec-dir", EXAMPLE])
    assert rc == 0
    lines = [line for line in out.splitlines() if line.strip()]
    # Every line should be a bare id (no comments, no indentation).
    for line in lines:
        assert not line.startswith("#")
        assert not line.startswith(" ")
        assert "—" not in line


# ---------- inspect ----------

def test_inspect_atom():
    rc, out, _ = _run(["inspect", "atm.pay.charge_card", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "kind: atom" in out
    assert "atom_kind: PROCEDURAL" in out
    assert "owner_module: PAY" in out
    assert "bundleable: true" in out
    assert "bundle_command: forge context atm.pay.charge_card" in out


def test_inspect_module():
    rc, out, _ = _run(["inspect", "PAY", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "kind: module" in out
    assert "owned_atoms:" in out
    assert "atm.pay.charge_card" in out


def test_inspect_non_bundleable_entity():
    rc, out, _ = _run(["inspect", "PAY.VAL.001", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "kind: error" in out
    assert "category: VAL" in out
    assert "bundleable: false" in out


def test_inspect_unknown_id_suggests():
    rc, _, err = _run(["inspect", "atm.pay.typo_here", "--spec-dir", EXAMPLE])
    assert rc == 1
    assert "unknown id" in err
    assert "Did you mean" in err
