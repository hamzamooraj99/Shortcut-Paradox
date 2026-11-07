import json

from fading_trails.config import settings_for
from fading_trails.employees import fake_factory
from fading_trails.judge import KeywordJudge
from fading_trails.results import export
from fading_trails.runner import Run


def test_export_for_the_results_page(tmp_path):
    runs = tmp_path / "runs"
    for setup, kw in (("2.7", {}), ("3.2", {"back_room_day": 2})):
        s = settings_for(setup, employees=12, days=4, turns_per_day=8)
        Run(s, runs / s.run_id, fake_factory(**kw), KeywordJudge()).run()
    s = settings_for("1.6", repeat=1, days=4, turns_per_day=8)
    Run(s, runs / s.run_id, fake_factory(), KeywordJudge()).run(stop_after_day=1)
    out = tmp_path / "results"
    assert export(runs, out) == 3
    idx = json.loads((out / "index.json").read_text())
    status = {r["run_id"]: r["status"] for r in idx["runs"]}
    assert status == {"2.7_r0": "done", "3.2_r0": "done", "1.6_r1": "running"}
    assert len(json.loads((out / "setups.json").read_text())["rows"]) == 2
    assert (out / "index.html").exists()
    rep = json.loads((out / "runs" / "2.7_r0.json").read_text())
    assert [d["day"] for d in rep["days"]] == [1, 2, 3, 4]
    assert len(rep["days"][0]["turns"]) == 8
    t = rep["days"][0]["turns"][0]
    assert len(t["acts"]) == 12 and len(t["wiki"]) >= 2 and set(t["desks"]) >= {"E01", "E12"}
    assert len(rep["days"][2]["joined"]) == 4 and len(rep["days"][2]["left"]) == 4
    joined = rep["days"][2]["joined"][0]
    assert rep["roster"][joined]["name"] and rep["roster"][joined]["replaces"]
    closes = [a for d in rep["days"] for tr in d["turns"] for a in tr["acts"] if a["tool"] == "close_ticket"]
    assert closes and all(any(x.startswith("hidden tests") for x in a["tags"]) for a in closes)
    br = json.loads((out / "runs" / "3.2_r0.json").read_text())["back_room"]
    assert len(br) == 12 and all(f["label"] == "cheat" and f["day"] == 2 for f in br)
