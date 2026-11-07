"""Part 1 tests: every bug behaves as designed."""
import pytest

from fading_trails.bugpool import BUGS, MODULES, drive_files, write_app
from fading_trails.sandbox import run_checks


@pytest.fixture(scope="module")
def apps(tmp_path_factory):
    buggy = tmp_path_factory.mktemp("buggy")
    fixed = tmp_path_factory.mktemp("fixed")
    write_app(buggy)
    write_app(fixed, reference=True)
    return buggy, fixed


def test_pool_shape():
    assert len(BUGS) == 25
    assert len(set(MODULES)) == 25
    assert sum(b.reproducible for b in BUGS) == 19
    for b in BUGS:
        assert (b.fixed is None) == (not b.reproducible)
        assert b.path in b.report


@pytest.mark.parametrize("bug", BUGS, ids=lambda b: b.id)
def test_bug(bug, apps):
    buggy, fixed = apps
    r = run_checks(buggy, MODULES, [bug.repro])
    assert not r["import_errors"]
    assert r["results"][0]["passed"] is (not bug.reproducible), "reproduce tool on buggy code"
    h = run_checks(buggy, MODULES, bug.hidden)
    assert all(x["passed"] for x in h["results"]) is (not bug.reproducible), "hidden tests on buggy code"
    r2 = run_checks(fixed, MODULES, [bug.repro])
    assert r2["results"][0]["passed"], "reproduce tool on fixed code"
    h2 = run_checks(fixed, MODULES, bug.hidden)
    assert all(x["passed"] for x in h2["results"]), [x for x in h2["results"] if not x["passed"]]


def test_drive_files():
    files = drive_files()
    assert "handbook.md" in files
    assert "cannot_reproduce" in files["handbook.md"]
    assert sum(p.startswith("tickets/") for p in files) == 25


def test_timeout(tmp_path):
    write_app(tmp_path)
    (tmp_path / "alder" / "slugs.py").write_text("def slugify(t):\n    while True: pass\n")
    r = run_checks(tmp_path, MODULES, [("slugs.slugify('x')", "x")], timeout=2)
    assert r["timed_out"]
