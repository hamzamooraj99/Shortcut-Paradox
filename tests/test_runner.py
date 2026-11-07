from collections import Counter

import pytest

from fading_trails.config import settings_for
from fading_trails.employees import fake_factory
from fading_trails.judge import KeywordJudge
from fading_trails.logbook import read_events
from fading_trails.runner import Run, planted_roles, ticket_schedule

SMALL = dict(days=4, tickets_per_day=2, turns_per_day=12)


def run(tmp_path, setup, repeat=0, stop=None, **kw):
    s = settings_for(setup, repeat=repeat, **{**SMALL, **kw.pop("settings", {})})
    r = Run(s, tmp_path / s.run_id, fake_factory(**kw), KeywordJudge())
    return r, r.run(stop_after_day=stop)


def test_schedule_is_replayable_and_distinct():
    s = settings_for("1.6", repeat=2, days=8, tickets_per_day=3)
    a = ticket_schedule(s, 4)
    assert a == ticket_schedule(settings_for("2.9", repeat=2, days=8, tickets_per_day=3), 4)
    flat = [t for d in a.values() for t in d]
    assert len(flat) == len(set(flat)) == 24
    assert ticket_schedule(settings_for("1.6", repeat=3, days=8, tickets_per_day=3), 4) != a
    with pytest.raises(ValueError):
        ticket_schedule(settings_for("1.6", days=9, tickets_per_day=3), 0)


def test_planted_roles():
    assert Counter(planted_roles(settings_for("2.7")).values()) == {"normal": 8, "bad": 2, "good": 2}
    assert Counter(planted_roles(settings_for("2.1")).values()) == {"normal": 10, "bad": 2}
    assert set(planted_roles(settings_for("1.6")).values()) == {"normal"}


def test_full_team_run(tmp_path):
    r, status = run(tmp_path, "1.6")
    assert status == "done" and r.done_file.exists()
    ev = read_events(r.dir)
    kinds = Counter(e["event"] for e in ev)
    assert kinds["close"] == 12 * 8
    assert kinds["diary"] == 12 * 4
    assert kinds["wiki_snapshot"] == 4 * 12              # after every turn
    assert kinds["broken_call"] == 0
    assert kinds["note_written"] == 12                   # one note each on day 2
    # every action logged before its result
    for a, b in zip(ev, ev[1:]):
        if b["event"] == "result":
            assert a["event"] in ("action", "close", "note_open", "note_written", "drive_write", "ticket_unfinished")
    assert Run(r.s, r.dir, fake_factory(), KeywordJudge()).run() == "already done"


def test_solo_runs(tmp_path):
    r, _ = run(tmp_path, "1.1")
    ev = read_events(r.dir)
    assert not [e for e in ev if e["event"] in ("wiki_snapshot", "topup", "note_open")]
    r, _ = run(tmp_path, "1.2")
    ev = read_events(r.dir)
    assert [e for e in ev if e["event"] == "note_open"] and not [e for e in ev if e["event"] == "topup"]


def test_planted_workers_leave_halfway(tmp_path):
    r, _ = run(tmp_path, "2.7")
    ev = read_events(r.dir)
    left = [e for e in ev if e["event"] == "worker_left"]
    joined = [e for e in ev if e["event"] == "worker_joined"]
    assert len(left) == len(joined) == 4 and all(e["day"] == 3 for e in left)
    start = ev[0]
    assert start["halfway_day"] == 2 and len(start["planted"]) == 4
    planted = set(start["planted"])
    late = [e for e in ev if e["event"] == "action" and e["day"] >= 3 and e["employee"] in planted]
    assert not late
    assert {e["employee"] for e in joined} == {"E13", "E14", "E15", "E16"}


def test_back_room_run(tmp_path):
    r, _ = run(tmp_path, "3.2", back_room_day=3)
    w = [e for e in read_events(r.dir) if e["event"] == "drive_write"]
    assert len(w) == 12 and all(e["day"] == 3 and e["label"] == "cheat" for e in w)


def test_resume_matches_uninterrupted(tmp_path):
    a, _ = run(tmp_path / "a", "1.5")
    b, status = run(tmp_path / "b", "1.5", stop=2)
    assert status == "stopped"
    b2 = Run(b.s, b.dir, fake_factory(), KeywordJudge())
    assert b2.run() == "done"
    strip = lambda evs: [{k: v for k, v in e.items() if k != "ts"} for e in evs]
    assert strip(read_events(a.dir)) == strip(read_events(b.dir))


def test_crash_mid_day_resumes(tmp_path):
    s = settings_for("1.6", **SMALL)
    calls = {"n": 0}

    def flaky(emp_id, name, role, office):
        from fading_trails.employees import FakeEmployee
        e = FakeEmployee(emp_id, name, role, office)
        orig = e.act

        def act(obs):
            calls["n"] += 1
            if calls["n"] == 200:
                raise RuntimeError("API down")
            return orig(obs)
        e.act = act
        return e

    r = Run(s, tmp_path / "x", flaky, KeywordJudge(), parallel=False)
    with pytest.raises(RuntimeError):
        r.run()
    assert Run(s, tmp_path / "x", fake_factory(), KeywordJudge()).run() == "done"
    ref, _ = run(tmp_path / "ref", "1.6")
    strip = lambda evs: [{k: v for k, v in e.items() if k != "ts"} for e in evs]
    assert strip(read_events(tmp_path / "x")) == strip(read_events(ref.dir))
