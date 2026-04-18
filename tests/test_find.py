"""Tests for `forge find` — the substring-match CLI search command."""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from cli.forge import main

EXAMPLE = str(Path(__file__).resolve().parent.parent / "src" / "example")


def _run(args: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(args)
    return rc, out.getvalue(), err.getvalue()


# ---------- Basic matches ----------

def test_find_by_id_substring():
    rc, out, _ = _run(["find", "charge_card", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "atm.pay.charge_card" in out
    assert "[id" in out  # id match signal present


def test_find_by_description_substring():
    rc, out, _ = _run(["find", "declined", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "PAY.EXT.003" in out
    assert "[desc]" in out  # only description matched, not id


def test_find_matches_both_id_and_description_rank_higher():
    rc, out, _ = _run(["find", "charge", "--spec-dir", EXAMPLE])
    assert rc == 0
    lines = [l for l in out.splitlines() if l.startswith("  ")]
    assert lines
    # First result should have [id+desc] signal (both matched)
    assert "[id+desc]" in lines[0]


# ---------- Kind filter ----------

def test_find_kind_filter_atoms_only():
    rc, out, _ = _run(["find", "charge", "--kind", "atom", "--spec-dir", EXAMPLE])
    assert rc == 0
    for line in out.splitlines():
        if line.startswith("  "):
            parts = line.split()
            # Second column after ID is kind.
            assert parts[1] == "atom"


def test_find_kind_filter_errors_only():
    rc, out, _ = _run(["find", "amount", "--kind", "error", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "PAY.VAL.001" in out
    assert "atm.pay" not in out


# ---------- Limit ----------

def test_find_limit_custom():
    rc, out, _ = _run(["find", "charge", "--limit", "3", "--spec-dir", EXAMPLE])
    assert rc == 0
    lines = [l for l in out.splitlines() if l.startswith("  ")]
    assert len(lines) == 3


def test_find_limit_zero_means_unlimited():
    rc, out, _ = _run(["find", "charge", "--limit", "0", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "showing top" not in out  # no truncation message


# ---------- No matches / error cases ----------

def test_find_no_matches():
    rc, out, _ = _run(["find", "nonexistent_query_xyz_123", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "no matches" in out


def test_find_empty_query_fails():
    rc, _, err = _run(["find", "  ", "--spec-dir", EXAMPLE])
    assert rc == 1
    assert "non-empty" in err


# ---------- Ranking ----------

def test_find_ranking_bundleable_kinds_first_on_ties():
    # "amount" matches many entities; bundleable atoms should rank above
    # errors/types when scores are equal.
    rc, out, _ = _run(["find", "amount", "--spec-dir", EXAMPLE])
    assert rc == 0
    lines = [l for l in out.splitlines() if l.startswith("  ")]
    assert lines
    parts = lines[0].split()
    # First match should be a bundleable kind (atom/module/flow/journey/artifact)
    assert parts[1] in ("atom", "module", "flow", "journey", "artifact")


# ---------- Case insensitivity ----------

def test_find_is_case_insensitive():
    _, out_lower, _ = _run(["find", "charge", "--spec-dir", EXAMPLE])
    _, out_upper, _ = _run(["find", "CHARGE", "--spec-dir", EXAMPLE])
    ids_lower = {l.split()[0] for l in out_lower.splitlines() if l.startswith("  ")}
    ids_upper = {l.split()[0] for l in out_upper.splitlines() if l.startswith("  ")}
    assert ids_lower == ids_upper
