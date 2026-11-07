from fading_trails.__main__ import main
from fading_trails.config import settings_for
from fading_trails.judge import LLMJudge
from fading_trails.llm import LLMClient, llm_factory
from fading_trails.pilot import later_day_factor, pilot_report
from fading_trails.runner import Run
from test_llm import scripted_model


def test_pilot_report_compares_models(tmp_path, capsys):
    for model in ("deepseek-v4-flash", "qwen3.5-397b"):
        client = LLMClient("groq", model, post=lambda url, headers, json, timeout: scripted_model(json))
        for setup in ("1.6", "2.1"):
            s = settings_for(setup, employees=4, days=2, turns_per_day=6, tickets_per_day=1)
            Run(s, tmp_path / f"runs_pilot_{model}" / s.run_id, llm_factory(client), LLMJudge(client),
                meta={"model": model, "judge_model": model}).run()
    rep = pilot_report([str(tmp_path / "runs_pilot_*")])
    assert "| deepseek-v4-flash |" in rep and "| qwen3.5-397b |" in rep
    assert "Typical seconds per step" in rep and "Planted bad workers who cheated" in rep
    main(["pilot", "--runs-dir", str(tmp_path / "runs_pilot_*"), "--out", str(tmp_path / "rep.md")])
    assert "Pilot report" in (tmp_path / "rep.md").read_text()


def test_later_day_factor():
    assert later_day_factor({1: [100]}, 8) == 1.0
    assert later_day_factor({1: [100], 2: [100], 3: [100]}, 8) == 1.0
    f = later_day_factor({1: [100], 2: [110], 3: [120]}, 8)   # +10 a day: days 1-8 average 135 vs 110
    assert abs(f - 135 / 110) < 1e-9
