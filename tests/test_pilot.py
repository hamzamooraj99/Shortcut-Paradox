from fading_trails.__main__ import main
from fading_trails.config import settings_for
from fading_trails.judge import LLMJudge
from fading_trails.llm import LLMClient, llm_factory
from fading_trails.pilot import pilot_report
from fading_trails.runner import Run
from test_llm import scripted_model


def test_pilot_report(tmp_path, capsys):
    s = settings_for("1.6", employees=3, days=2, turns_per_day=10, tickets_per_day=2)
    client = LLMClient("groq", "m", post=lambda url, headers, json, timeout: scripted_model(json))
    Run(s, tmp_path / "pilot" / s.run_id, llm_factory(client), LLMJudge(client)).run()
    rep = pilot_report(tmp_path / "pilot", price_in=0.1, price_out=0.4)
    assert "Tokens per employee per day" in rep and "All 95 runs" in rep
    assert "cheat rate 0%" in rep and "NOT met yet" in rep
    assert "Planted cheat note" in rep and "Planted bad worker instruction" in rep
    main(["pilot", "--runs-dir", str(tmp_path / "pilot"), "--price-in", "0.1", "--price-out", "0.4"])
    assert "Pilot report" in capsys.readouterr().out
