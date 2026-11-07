import json
import re

import pytest

import fading_trails.llm as llm
from fading_trails.config import settings_for
from fading_trails.judge import LLMJudge
from fading_trails.llm import LLMClient, LLMEmployee, ProviderError, llm_factory
from fading_trails.logbook import read_events
from fading_trails.office import TOOL_SPECS
from fading_trails.runner import Run
from fading_trails.scorer import score_run


class Resp:
    def __init__(self, code, data):
        self.status_code, self._d = code, data
        self.text = json.dumps(data)

    def json(self):
        return self._d


def groq_tool(name, args, usage=None):
    return Resp(200, {"choices": [{"message": {"content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}],
        "usage": usage or {"prompt_tokens": 100, "completion_tokens": 10,
                           "completion_tokens_details": {"reasoning_tokens": 4}}})


def groq_text(text):
    return Resp(200, {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 5, "completion_tokens": 5}})


class Recorder:
    def __init__(self, replies):
        self.replies, self.bodies = list(replies), []

    def __call__(self, url, headers, json, timeout):
        self.bodies.append(json)
        r = self.replies.pop(0)
        return r(json) if callable(r) else r


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


TOOLS = [{"name": n, "description": TOOL_SPECS[n][0], "parameters": TOOL_SPECS[n][1]} for n in ("read_ticket", "close_ticket")]


def test_groq_request_and_parse():
    rec = Recorder([groq_tool("read_ticket", {"ticket_id": "ALD-101"})])
    c = LLMClient("groq", "m", post=rec)
    tool, args, err, usage = c.decide("You are Ana.", [{"role": "user", "content": "hi"}], TOOLS)
    assert (tool, args, err) == ("read_ticket", {"ticket_id": "ALD-101"}, None)
    b = rec.bodies[0]
    assert b["tool_choice"] == "required" and b["parallel_tool_calls"] is False
    assert b["tools"][0]["type"] == "function" and b["tools"][0]["function"]["name"] == "read_ticket"
    assert b["messages"][0]["role"] == "system" and b["reasoning_effort"] == "low"
    assert usage["input_tokens"] == 100 and usage["reasoning_tokens"] == 4


def test_adaption_request_and_parse():
    reply = Resp(200, {"output": [{"type": "reasoning"}, {"type": "function_call", "name": "close_ticket",
                                                          "arguments": '{"ticket_id": "ALD-1", "resolution": "fixed"}',
                                                          "call_id": "x"}],
                       "output_text": "", "usage": {"input_tokens": 50, "output_tokens": 7,
                                                    "input_tokens_details": {"cached_tokens": 20},
                                                    "output_tokens_details": {"reasoning_tokens": 3}}})
    rec = Recorder([reply])
    c = LLMClient("adaption", "deepseek-v4-flash", post=rec)
    tool, args, err, usage = c.decide("sys", [{"role": "user", "content": "hi"}], TOOLS)
    assert tool == "close_ticket" and args["resolution"] == "fixed"
    b = rec.bodies[0]
    assert b["agentic_memory"] is False and b["store"] is False
    assert b["tools"][0] == {"type": "function", **TOOLS[0]} and b["instructions"].startswith("sys")
    assert usage["cached_tokens"] == 20 and usage["reasoning_tokens"] == 3


def test_drops_unsupported_reasoning_and_retries_server_errors():
    rec = Recorder([Resp(400, {"error": "reasoning_effort not supported"}), Resp(503, {}),
                    groq_tool("read_ticket", {"ticket_id": "ALD-1"})])
    c = LLMClient("groq", "m", post=rec)
    assert c.decide("s", [], TOOLS)[0] == "read_ticket"
    assert "reasoning_effort" not in rec.bodies[-1] and c.reasoning is None


def test_auth_error_is_raised():
    c = LLMClient("groq", "m", post=Recorder([Resp(401, {"error": "bad key"})]))
    with pytest.raises(ProviderError):
        c.decide("s", [], TOOLS)


def test_think_tags_removed():
    c = LLMClient("groq", "m", post=Recorder([groq_text("<think>hmm</think>cheat")]))
    assert c.complete("x")[0] == "cheat"


class FakeOffice:
    def validate(self, tool, args):
        return None if tool == "read_ticket" and isinstance(args, dict) and "ticket_id" in args else "bad"


def test_employee_retries_once_then_reports_broken():
    rec = Recorder([groq_text("I think I will..."), groq_tool("read_ticket", {"ticket_id": "ALD-1"}),
                    groq_text("no"), groq_tool("read_ticket", {})])
    e = LLMEmployee("E01", "Ana", "normal", FakeOffice(), LLMClient("groq", "m", post=rec))
    e.start_day(1, "brief", TOOLS)
    assert e.act("obs") == ("read_ticket", {"ticket_id": "ALD-1"})
    assert e.act("obs2") is None and e.last_error == "bad"
    assert len(e.pop_usage()) == 4
    assert e.history[1]["content"].startswith("Action: read_ticket")


def scripted_model(body):
    """A stand-in model: works each ticket honestly (reproduce, then close as can't-reproduce)."""
    if not body.get("tools"):
        prompt = body["messages"][-1]["content"]
        return groq_text("other" if "Label the note" in prompt else "Closed my tickets.")
    convo = [m["content"] for m in body["messages"] if m["role"] != "system"]
    last = convo[-1]
    m = re.search(r"Your open tickets: (ALD-\d+)", last)
    if not m:
        return groq_text("nothing to do")
    t = m.group(1)
    done_repro = any(f"Reproduce tool - {t}" in x for x in convo)
    if not done_repro:
        return groq_tool("run_reproduce", {"ticket_id": t})
    return groq_tool("close_ticket", {"ticket_id": t, "resolution": "cannot_reproduce"})


def test_full_run_with_ai_employee_plumbing(tmp_path):
    s = settings_for("1.6", employees=3, days=2, turns_per_day=10, tickets_per_day=2)
    client = LLMClient("groq", "m", post=lambda url, headers, json, timeout: scripted_model(json))
    run = Run(s, tmp_path / s.run_id, llm_factory(client), LLMJudge(client))
    assert run.run() == "done"
    ev = read_events(run.dir)
    assert sum(e["event"] == "close" for e in ev) == 12
    assert any(e["event"] == "llm_usage" and e.get("purpose") == "diary" for e in ev)
    assert all(e["text"] == "Closed my tickets." for e in ev if e["event"] == "diary")
    row = score_run(run.dir)
    assert row["m1_cheat_rate"] == 0.0 and row["m2_tip_rate"] == 1.0 and row["m21_broken_call_rate"] == 0.0
