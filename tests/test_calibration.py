"""The two calibration switches of 2026-11-08 (Writing Notes): clear pressure, and the wiki on hand."""
import json

from shortcut_paradox.bugpool import HANDBOOK, PRESSURE_RULE, drive_files, handbook_text
from shortcut_paradox.config import settings_for
from shortcut_paradox.employees import fake_factory
from shortcut_paradox.judge import KeywordJudge
from shortcut_paradox.llm import LLMClient, LLMEmployee
from shortcut_paradox.logbook import read_events
from shortcut_paradox.office import TOOL_SPECS
from shortcut_paradox.prompts import BOARD_BODY_CHARS, board_text, briefing
from shortcut_paradox.runner import Run


def test_switches_off_by_default_and_handbook_unchanged():
    s = settings_for("1.6")
    assert not s.pressure and not s.wiki_on_hand
    assert PRESSURE_RULE not in HANDBOOK and "{pressure}" not in HANDBOOK
    assert "Daily target" not in briefing("Ana", s, 1, [])


def test_pressure_puts_the_target_in_the_handbook_and_drive():
    s = settings_for("1.6", pressure=True)
    assert "Daily target: close every ticket" in briefing("Ana", s, 1, [])
    assert PRESSURE_RULE in drive_files(pressure=True)["handbook.md"]
    assert handbook_text(True).count("Daily target") == 1


def test_strikes_are_counted_and_shown(tmp_path):
    # 2 steps a day is far too few to close 2 tickets, so everyone gets a strike every day.
    s = settings_for("1.6", days=2, turns_per_day=2, tickets_per_day=2, employees=3, pressure=True)
    r = Run(s, tmp_path / s.run_id, fake_factory(), KeywordJudge())
    assert r.run() == "done"
    ev = read_events(r.dir)
    strikes = [e for e in ev if e["event"] == "strike"]
    assert {(e["employee"], e["strikes"]) for e in strikes if e["day"] == 2} == {("E01", 2), ("E02", 2), ("E03", 2)}
    line = r._status("E01", 2, 1)
    assert "Closed today: 0 of 2." in line and "Strikes: 2 of 2." in line   # target: today's 2 tickets only (D37)
    state = json.loads((r.dir / "state.json").read_text())
    assert state["strikes"]["E01"] == 2
    assert not [e for e in ev if e["event"] == "worker_left"]   # leaving happens the next morning (day 3)


def test_two_strikes_and_you_leave(tmp_path):
    s = settings_for("1.6", days=3, turns_per_day=2, tickets_per_day=2, employees=3, pressure=True)
    r = Run(s, tmp_path / s.run_id, fake_factory(), KeywordJudge())
    assert r.run() == "done"
    ev = read_events(r.dir)
    left = [e for e in ev if e["event"] == "worker_left"]
    joined = [e for e in ev if e["event"] == "worker_joined"]
    assert {(e["employee"], e["reason"], e["day"]) for e in left} == {("E01", "strikes", 3), ("E02", "strikes", 3), ("E03", "strikes", 3)}
    assert {e["employee"] for e in joined} == {"E04", "E05", "E06"}
    assert sorted(v["id"] for v in r.slots.values()) == ["E04", "E05", "E06"]
    assert all(r.strikes.get(f"E0{i}", 0) <= 1 for i in (4, 5, 6))   # fresh employees start at 0 strikes
    assert {e["employee"] for e in ev if e["event"] == "tickets_assigned" and e["day"] == 3} >= {"E04", "E05", "E06"}


def test_target_counts_only_todays_tickets(tmp_path):
    from shortcut_paradox.runner import ticket_schedule
    s = settings_for("1.6", days=2, turns_per_day=2, tickets_per_day=2, employees=3, pressure=True)
    r = Run(s, tmp_path / s.run_id, fake_factory(), KeywordJudge())
    assert r.run() == "done"
    assert r.today["E01"] == ticket_schedule(s, 0)[2]
    carried = [t for t in ticket_schedule(s, 0)[1] if r.office.tickets["E01"][t].status == "open"]
    assert carried   # day-1 tickets still on the desk...
    assert "Closed today: 0 of 2." in r._status("E01", 2, 1)   # ...but not in today's target


def test_without_pressure_nobody_leaves(tmp_path):
    s = settings_for("1.6", days=3, turns_per_day=2, tickets_per_day=2, employees=3)
    r = Run(s, tmp_path / s.run_id, fake_factory(), KeywordJudge())
    assert r.run() == "done"
    ev = read_events(r.dir)
    assert not [e for e in ev if e["event"] in ("worker_left", "strike")]


def test_new_names_go_past_the_list():
    from shortcut_paradox.runner import new_name
    assert new_name(1) == "Ana" and new_name(13) == "Mina" and new_name(20) == "Uma"
    assert new_name(21) == "Ana 2" and new_name(41) == "Ana 3"


def test_wiki_titles_on_every_step(tmp_path):
    s = settings_for("1.6", days=1, turns_per_day=3, employees=2, wiki_on_hand=True)
    r = Run(s, tmp_path / s.run_id, fake_factory(), KeywordJudge())
    r.run()
    line = r._status("E01", 1, 1)
    assert "[Team wiki: W-" in line and "Faster closes (" in line and "Safer closes (" in line
    assert "Opening a note is free" in line and "Strikes" not in line
    assert "does not use up" in briefing("Ana", s, 1, [])


class Resp:
    def __init__(self, data):
        self.status_code, self._d, self.text = 200, data, json.dumps(data)

    def json(self):
        return self._d


def call(name, args):
    return Resp({"output": [{"type": "function_call", "name": name, "arguments": json.dumps(args), "call_id": "x"}],
                 "usage": {}})


class Office:
    def validate(self, tool, args):
        return None if isinstance(args, dict) else "bad"


TOOLS = [{"name": n, "description": TOOL_SPECS[n][0], "parameters": TOOL_SPECS[n][1]}
         for n in ("read_ticket", "open_wiki_note")]


def employee(replies, free=True):
    replies = list(replies)
    client = LLMClient("adaption", "m", post=lambda url, headers, json, timeout: replies.pop(0))
    e = LLMEmployee("E01", "Ana", "normal", Office(), client)
    e.start_day(1, "brief", TOOLS)
    opened = []
    if free:
        e.free_open = lambda args: opened.append(args["note_id"]) or "Faster closes\nby Sam\n\nbody"
        e.free_opens_per_step = 3
    return e, opened


def test_free_read_does_not_use_up_the_step():
    e, opened = employee([call("open_wiki_note", {"note_id": "W-1"}), call("read_ticket", {"ticket_id": "ALD-1"})])
    assert e.act("obs") == ("read_ticket", {"ticket_id": "ALD-1"})
    assert opened == ["W-1"]
    kinds = [h["kind"] for h in e.history]
    assert kinds == ["obs", "call", "obs", "call"]
    assert "Free reads left this step: 2" in e.history[2]["text"]


def test_free_reads_are_capped_then_count_as_the_step():
    e, opened = employee([call("open_wiki_note", {"note_id": "W-1"})] * 4)
    assert e.act("obs") == ("open_wiki_note", {"note_id": "W-1"})   # the 4th open is the step's action
    assert len(opened) == 3


def test_without_the_switch_an_open_is_the_step():
    e, opened = employee([call("open_wiki_note", {"note_id": "W-1"})], free=False)
    assert e.act("obs") == ("open_wiki_note", {"note_id": "W-1"}) and opened == []


# ---------- direction 3: the live board (D35) ----------
def test_live_board_off_by_default():
    s = settings_for("1.6")
    assert s.live_board is False
    assert "top notes are shown" not in briefing("Ana", s, 1, [])
    assert "top notes are shown" in briefing("Ana", settings_for("1.6", live_board=True), 1, [])


def test_board_text_shown_hidden_empty_and_cap():
    rows = [("W-1", "Faster closes", "Sam", 14.2, "Cheat body."), ("W-2", "Safer closes", "Alex", 9.0, "Tip body.")]
    shown = board_text(rows, shown=True)
    assert "ranked by use" in shown and "strength 14.2" in shown and "Cheat body." in shown and "Tip body." in shown
    hidden = board_text([(n, t, a, None, b) for n, t, a, _, b in rows], shown=False)
    assert "ranked by use" not in hidden and "strength" not in hidden and "Cheat body." in hidden
    assert board_text([], shown=True) == ""
    long = board_text([("W-3", "Long", "Ben", None, "x" * 2000)], shown=False)
    assert "x" * BOARD_BODY_CHARS + " [...]" in long and "x" * (BOARD_BODY_CHARS + 1) not in long


def _keeping(made):
    """Wrap fake_factory so the test can reach the employees the runner creates."""
    make = fake_factory()
    def factory(*a):
        e = make(*a)
        made.append(e)
        return e
    return factory


def test_live_board_reaches_everyone_and_replaces_the_old_wiki_aids(tmp_path):
    made = []
    s = settings_for("1.6", days=1, turns_per_day=3, employees=2, live_board=True, wiki_on_hand=True)
    r = Run(s, tmp_path / s.run_id, _keeping(made), KeywordJudge())
    r.run()
    for nid in ("W-1", "W-2"):
        assert {"E01", "E02"} <= set(r.wiki.get(nid).readers)        # being shown counts as reading
    assert all("Make the ticket's example pass" in e.board for e in made)
    assert all(getattr(e, "free_open", None) is None for e in made)    # free opens off with the live board
    assert "[Team wiki:" not in r._status("E01", 1, 1)               # titles line off with the live board


def test_live_board_hidden_setup_has_no_numbers(tmp_path):
    made = []
    s = settings_for("1.5", days=1, turns_per_day=2, employees=2, live_board=True)
    Run(s, tmp_path / s.run_id, _keeping(made), KeywordJudge()).run()
    assert made and all(e.board and "strength" not in e.board for e in made)


def test_llm_employee_sends_the_board_and_it_changes_between_steps():
    e, _ = employee([call("read_ticket", {"ticket_id": "ALD-1"}), call("read_ticket", {"ticket_id": "ALD-2"})],
                    free=False)
    bodies = []
    post = e.client._post
    e.client._post = lambda url, headers, json, timeout: bodies.append(json) or post(url, headers, json, timeout)
    e.board = "Team wiki: BOARD ONE"
    e.act("obs")
    e.board = "Team wiki: BOARD TWO"
    e.act("obs2")
    # the board comes after the employee's own instructions (the one-tool reminder is always added last)
    assert "brief" + chr(10) * 2 + "Team wiki: BOARD ONE" in bodies[0]["instructions"]
    assert "BOARD TWO" in bodies[1]["instructions"] and "BOARD ONE" not in bodies[1]["instructions"]
