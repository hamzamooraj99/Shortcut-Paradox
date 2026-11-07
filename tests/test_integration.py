"""Final integration test: every setup runs from one command and is scored."""
import csv

from fading_trails.__main__ import main


def test_all_19_setups_end_to_end(tmp_path):
    runs, results = str(tmp_path / "runs"), str(tmp_path / "results")
    main(["run", "--setups", "all", "--repeats", "1", "--runs-dir", runs, "--jobs", "4",
          "--employees", "6", "--days", "4", "--turns-per-day", "10", "--tickets-per-day", "2"])
    main(["score", "--runs-dir", runs, "--out", results])
    sheets = sorted(p.name for p in (tmp_path / "results").glob("setup_*.csv"))
    # Part 3 stops after its first 2 runs only if nobody writes; with 1 repeat both run.
    assert len(sheets) == 19
    rows = list(csv.DictReader(open(tmp_path / "results" / "all_runs.csv")))
    assert all(r["m1_cheat_rate"] and r["m21_broken_call_rate"] == "0.0" for r in rows)
    by = {r["setup"]: r for r in rows}
    assert by["1.1"]["m4_cheat_strength_by_day"] == "" and by["1.4"]["m4_cheat_strength_by_day"] != ""
    assert by["2.7"]["m15_pusher_match"] != "" and by["3.2"]["m17_back_room_files"] != ""
