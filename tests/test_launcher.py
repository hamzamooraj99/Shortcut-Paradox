from fading_trails.__main__ import main, parse_setups

TINY = ["--employees", "3", "--days", "2", "--turns-per-day", "8", "--tickets-per-day", "2"]


def test_groups():
    assert len(parse_setups("all")) == 19
    assert parse_setups("part1,3.2")[-1] == "3.2"


def test_one_command_runs_and_skips(tmp_path, capsys):
    runs = str(tmp_path / "runs")
    main(["run", "--setups", "1.1,1.6", "--repeats", "2", "--runs-dir", runs, "--jobs", "2"] + TINY)
    assert len(list((tmp_path / "runs").glob("*/done.json"))) == 4
    capsys.readouterr()
    main(["run", "--setups", "1.1,1.6", "--repeats", "2", "--runs-dir", runs] + TINY)
    assert capsys.readouterr().out.count("already done") == 4
    main(["score", "--runs-dir", runs, "--out", str(tmp_path / "results")])
    assert (tmp_path / "results" / "setup_1.6.csv").read_text().count("\n") == 3


def test_part3_stop_rule(tmp_path, capsys):
    runs = str(tmp_path / "runs")
    main(["run", "--setups", "part3", "--repeats", "2", "--runs-dir", runs] + TINY)
    out = capsys.readouterr().out
    assert out.count("Part 3 stop rule") == 2          # repeat 1 of both Part 3 setups cancelled
    assert (tmp_path / "runs" / "PART3_CANCELLED.txt").exists()
    assert len(list((tmp_path / "runs").glob("*/done.json"))) == 2
