"""Tests for `forge find` — substring search against the example spec."""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from cli.forge import main

EXAMPLE = str(Path(__file__).resolve().parent.parent / "example" / "spec")


def _run(args: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(args)
    return rc, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# Basic matches
# ---------------------------------------------------------------------------

def test_find_by_id_substring():
    rc, out, _ = _run(["find", "short_link", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "linkhub.shortener.links.link_manager.short_link" in out
    assert "[id" in out


def test_find_by_description_substring():
    rc, out, _ = _run(["find", "alphanumeric", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "[desc]" in out or "[id+desc]" in out


def test_find_id_plus_desc_ranks_higher():
    rc, out, _ = _run(["find", "redirect", "--spec-dir", EXAMPLE])
    assert rc == 0
    lines = [l for l in out.splitlines() if l.startswith("  ")]
    assert lines
    assert "[id+desc]" in lines[0]


# ---------------------------------------------------------------------------
# Kind filter
# ---------------------------------------------------------------------------

def test_find_kind_filter_element():
    rc, out, _ = _run(["find", "link", "--kind", "element", "--spec-dir", EXAMPLE])
    assert rc == 0
    for line in out.splitlines():
        if line.startswith("  "):
            parts = line.split()
            assert parts[1] == "element"


def test_find_kind_filter_type():
    rc, out, _ = _run(["find", "Short", "--kind", "type", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "linkhub.shortener.types.ShortCode" in out
    assert "short_link" not in out  # element should not appear


# ---------------------------------------------------------------------------
# Limit
# ---------------------------------------------------------------------------

def test_find_limit_custom():
    rc, out, _ = _run(["find", "link", "--limit", "2", "--spec-dir", EXAMPLE])
    assert rc == 0
    lines = [l for l in out.splitlines() if l.startswith("  ")]
    assert len(lines) == 2


def test_find_limit_zero_means_unlimited():
    rc, out, _ = _run(["find", "link", "--limit", "0", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "showing top" not in out


# ---------------------------------------------------------------------------
# No matches / error cases
# ---------------------------------------------------------------------------

def test_find_no_matches():
    rc, out, _ = _run(["find", "xyzzy_no_such_thing_9999", "--spec-dir", EXAMPLE])
    assert rc == 0
    assert "no matches" in out


def test_find_empty_query_fails():
    rc, _, err = _run(["find", "   ", "--spec-dir", EXAMPLE])
    assert rc == 1
    assert "non-empty" in err


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------

def test_find_is_case_insensitive():
    _, out_lower, _ = _run(["find", "shortcode", "--spec-dir", EXAMPLE])
    _, out_upper, _ = _run(["find", "SHORTCODE", "--spec-dir", EXAMPLE])
    ids_lower = {l.split()[0] for l in out_lower.splitlines() if l.startswith("  ")}
    ids_upper = {l.split()[0] for l in out_upper.splitlines() if l.startswith("  ")}
    assert ids_lower == ids_upper
