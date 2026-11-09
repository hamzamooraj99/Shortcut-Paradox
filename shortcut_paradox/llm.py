"""Part 9: the AI employee and the connection to the model providers.

Providers:
- groq:     OpenAI-style chat completions (https://api.groq.com/openai/v1/chat/completions).
            Free tier, smoke tests only (risk note).
- adaption: Responses-style API, POST https://api.prod.adaptionlabs.ai/api/v1/responses
            (docs.adaptionlabs.ai, checked 2026-11-07). Every call sends agentic_memory=false,
            store=false and an explicit tool list, so Adaption's own memory never becomes a
            hidden second wiki (risk 3).

The conversation history is stored as provider-neutral records (an observation, a tool
call, or a plain note) and rendered per provider as native tool-call history: Adaption gets
function_call / function_call_output items, Groq gets assistant tool_calls / tool messages.
(D32: an earlier version kept past actions as "Action: tool {...}" text, and most models
copied that text instead of calling a tool.) Both providers must call a tool on action
calls (tool_choice=required). The diary call has no tools, so its history is rendered as
plain text.

Keys come from a .env file: GROQ_API_KEY, ADAPTION_API_KEY.
"""
import json
import os
import re
import random
import threading
import time
from pathlib import Path

import requests

from .prompts import DIARY_MAX_CHARS, DIARY_REQUEST

ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "adaption": "https://api.prod.adaptionlabs.ai/api/v1/responses",
}
KEY_NAMES = {"groq": "GROQ_API_KEY", "adaption": "ADAPTION_API_KEY"}
ONE_TOOL = "Respond by calling exactly one tool."
HISTORY_CHARS = 3000      # each stored observation is cut to this length
# D36: thinking and the written answer share one output limit. On diaries (no tools) qwen3.5-397b
# thought past 2,048 tokens and wrote nothing, so diaries get a larger limit and a longer timeout
# (a 2,048-token diary took up to 41 s). Action calls keep 2,048 and the default timeout.
DIARY_MAX_TOKENS = 8192
DIARY_TIMEOUT = 300
RATE_LIMIT_PATIENCE_SECONDS = 1800   # wait out "rate limit reached" replies for up to 30 minutes (Hamza, 2026-11-09)

# Client-side pacing (Adaption's request, 2026-11-09): at most MAX_RPM requests a minute from this process, evenly
# spaced, shared by every employee in the process. 0 = no pacing. Only the timing of calls changes.
MAX_RPM = 0.0
_pace_lock = threading.Lock()
_next_slot = [0.0]


def _pace():
    if MAX_RPM <= 0:
        return
    with _pace_lock:
        now = time.time()
        slot = max(now, _next_slot[0])
        _next_slot[0] = slot + 60.0 / MAX_RPM
    if slot > now:
        time.sleep(slot - now)


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except ImportError:
        pass


class ProviderError(Exception):
    pass


class LLMClient:
    def __init__(self, provider, model, reasoning="low", max_output_tokens=2048, timeout=120, post=None):
        load_env()
        self.provider, self.model = provider, model
        self.reasoning = None if reasoning in (None, "none", "omit") else reasoning
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout
        self._post = post or requests.post
        self.key = os.environ.get(KEY_NAMES[provider], "")
        if not self.key and post is None:
            raise SystemExit(f"Missing {KEY_NAMES[provider]}: put it in the .env file (see .env.example).")
        self._lock = threading.Lock()

    # ---------- requests ----------
    def _render(self, messages, as_text=False):
        """Turn history records into this provider's message format. Records:
        {"kind": "obs", "text"}            an observation; it is the output of the call just before it, if any
        {"kind": "call", "id", "tool", "args"}  a tool call the employee made
        {"kind": "note", "role", "text"}   a plain message
        Dicts without "kind" are passed through unchanged (the judge uses plain messages)."""
        out, prev = [], None
        for m in messages:
            k = m.get("kind")
            if k is None:
                out.append(m)
            elif k == "call":
                args = json.dumps(m["args"], ensure_ascii=False)
                if as_text:
                    out.append({"role": "assistant", "content": f"(used {m['tool']} {args})"})
                elif self.provider == "groq":
                    out.append({"role": "assistant", "content": None, "tool_calls": [
                        {"id": m["id"], "type": "function", "function": {"name": m["tool"], "arguments": args}}]})
                else:
                    out.append({"type": "function_call", "call_id": m["id"], "name": m["tool"], "arguments": args})
            elif k == "obs" and prev and prev.get("kind") == "call" and not as_text:
                if self.provider == "groq":
                    out.append({"role": "tool", "tool_call_id": prev["id"], "content": m["text"]})
                else:
                    out.append({"type": "function_call_output", "call_id": prev["id"], "output": m["text"]})
            else:
                out.append({"role": m.get("role", "user"), "content": m["text"]})
            prev = m
        return out

    def _payload(self, system, messages, tools, max_tokens=None):
        messages = self._render(messages, as_text=not tools)
        limit = max_tokens or self.max_output_tokens
        if self.provider == "groq":
            body = {"model": self.model, "messages": [{"role": "system", "content": system}] + messages,
                    "max_completion_tokens": limit}
            if tools:
                body["tools"] = [{"type": "function", "function": t} for t in tools]
                body["tool_choice"] = "required"
                body["parallel_tool_calls"] = False
            if self.reasoning:
                body["reasoning_effort"] = self.reasoning
            return body
        body = {"model": self.model, "instructions": system, "input": messages,
                "tools": [{"type": "function", **t} for t in tools] if tools else [],
                "tool_choice": "required" if tools else "none",
                "agentic_memory": False, "store": False, "max_output_tokens": limit}
        if self.reasoning:
            body["reasoning"] = {"effort": self.reasoning}
        return body

    def _call(self, system, messages, tools, purpose, max_tokens=None, timeout=None):
        body = self._payload(system, messages, tools, max_tokens)
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        delay = 2.0
        waits = {"retries": 0, "rate_limited": 0, "wait_seconds": 0.0}   # logged with the call (pilot report)
        limited = 0.0   # seconds spent waiting out rate-limit replies (Hamza, 2026-11-09: wait, do not crash)
        attempt = 0
        while attempt < 8:
            _pace()
            t0 = time.time()
            try:
                r = self._post(ENDPOINTS[self.provider], headers=headers, json=body, timeout=timeout or self.timeout)
            except requests.RequestException as e:
                err = f"network: {e}"
            else:
                if r.status_code == 200:
                    data = r.json()
                    return data, {**self._usage(data, time.time() - t0, purpose), **waits}
                err = f"HTTP {r.status_code}: {r.text[:300]}"
                if r.status_code == 400 and "tool_use_failed" in r.text:
                    # The provider rejected a malformed tool call from the model. That is the
                    # model's mistake, not ours: treat it as a reply with no valid tool call.
                    msg = r.text[:300]
                    return {"_malformed": msg}, {**self._usage({}, time.time() - t0, purpose), **waits}
                waits["rate_limited"] += r.status_code == 429
                if r.status_code == 400 and ("reasoning" in r.text) and self.reasoning:
                    # The model does not take a reasoning setting: drop it for good, once.
                    with self._lock:
                        self.reasoning = None
                    body = self._payload(system, messages, tools, max_tokens)
                    continue
                if r.status_code in (400, 401, 403, 404, 422):
                    raise ProviderError(err)
                if r.status_code == 429 and limited < RATE_LIMIT_PATIENCE_SECONDS:
                    # The provider asks us to retry after 60 seconds: wait it out (up to the patience limit)
                    # without using up one of the 8 attempts. Only the waiting changes, not what employees see.
                    pause = 60 + 5 * random.random()
                    limited += pause
                    waits["retries"] += 1
                    waits["wait_seconds"] = round(waits["wait_seconds"] + (time.time() - t0) + pause, 1)
                    time.sleep(pause)
                    continue
            attempt += 1
            pause = delay + random.random()
            waits["retries"] += 1
            waits["wait_seconds"] = round(waits["wait_seconds"] + (time.time() - t0) + pause, 1)
            time.sleep(pause)
            delay = min(delay * 2, 60)
        raise ProviderError(f"gave up after retries: {err}")

    def _usage(self, data, seconds, purpose):
        u = data.get("usage") or {}
        if self.provider == "groq":
            inp, out = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
            cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
            reasoning = (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
        else:
            inp, out = u.get("input_tokens", 0), u.get("output_tokens", 0)
            cached = (u.get("input_tokens_details") or {}).get("cached_tokens", 0)
            reasoning = (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
        out_u = {"purpose": purpose, "input_tokens": inp, "output_tokens": out, "cached_tokens": cached or 0,
                 "reasoning_tokens": reasoning or 0, "seconds": round(seconds, 3)}
        if self.provider == "adaption":
            # Adaption reports the billed cost of each call (checked 2026-11-08: it matches the price table exactly)
            # and whether a cache was written; Qwen 3.5 397B never writes one.
            out_u["cost"] = u.get("cost")
            out_u["cache_write_tokens"] = (u.get("input_tokens_details") or {}).get("cache_write_tokens") or 0
        return out_u

    # ---------- parsing ----------
    def _parse(self, data):
        """Return (tool_name, args_text, text). tool_name is None when no tool was called."""
        name, args, text = self._parse_raw(data)
        return name, args, re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()

    def _parse_raw(self, data):
        if self.provider == "groq":
            msg = (data.get("choices") or [{}])[0].get("message") or {}
            calls = msg.get("tool_calls") or []
            if calls:
                f = calls[0].get("function") or {}
                return f.get("name"), f.get("arguments") or "{}", msg.get("content") or ""
            return None, None, msg.get("content") or ""
        for item in data.get("output") or []:
            if item.get("type") == "function_call":
                return item.get("name"), item.get("arguments") or "{}", data.get("output_text") or ""
        return None, None, data.get("output_text") or ""

    # ---------- public ----------
    def decide(self, system, messages, tools):
        """One decision. Returns (tool, args or None, error or None, usage)."""
        data, usage = self._call(system + "\n\n" + ONE_TOOL, messages, tools, "action")
        if "_malformed" in data:
            return None, None, "the tool call was malformed (missing or wrong arguments)", usage
        name, args_text, text = self._parse(data)
        if not name:
            return None, None, f"no tool was called (reply was: {text[:200]!r})", usage
        try:
            args = json.loads(args_text) if args_text.strip() else {}
        except json.JSONDecodeError:
            return name, None, f"the arguments for {name} were not valid JSON", usage
        return name, args, None, usage

    def complete(self, prompt, purpose="text", system="", messages=None, max_tokens=None, timeout=None):
        """Plain text reply, no tools. Returns (text, usage)."""
        msgs = list(messages or []) + [{"role": "user", "content": prompt}]
        data, usage = self._call(system, msgs, [], purpose, max_tokens=max_tokens, timeout=timeout)
        _, _, text = self._parse(data)
        return text, usage


class LLMEmployee:
    def __init__(self, emp_id, name, role, office, client):
        self.id, self.name, self.role, self.office, self.client = emp_id, name, role, office, client
        self.history = []          # provider-neutral records, see LLMClient._render
        self.usage = []
        self.last_error = None
        self.calls = 0
        self.free_open = None          # set by the runner when wiki notes can be opened without using a step
        self.free_opens_per_step = 0
        self.board = ""                # the live board (D35), set by the runner on every step when it is on

    def start_day(self, day, briefing, tools):
        self.system, self.tools, self.history = briefing, tools, []
        self.board = ""

    def _system(self):
        return self.system if not self.board else self.system + "\n\n" + self.board

    def act(self, observation):
        self.history.append({"kind": "obs", "text": observation[:HISTORY_CHARS]})
        messages = list(self.history)
        free_left = self.free_opens_per_step if self.free_open else 0
        for attempt in range(2):                 # one retry (risk 5)
            tool, args, err, usage = self.client.decide(self._system(), messages, self.tools)
            usage["attempt"] = attempt
            self.usage.append(usage)
            # Free wiki reads: the note is opened at once, and the employee then decides again.
            while (err is None and tool == "open_wiki_note" and free_left > 0
                   and self.office.validate(tool, args) is None):
                free_left -= 1
                self.calls += 1
                call = {"kind": "call", "id": f"call_{self.id}_{self.calls}", "tool": tool, "args": args}
                obs = {"kind": "obs", "text": (self.free_open(args)[:HISTORY_CHARS] +
                       f"\n\n[That read was free. Free reads left this step: {free_left}. "
                       "Now choose your action for this step.]")}
                self.history += [call, obs]
                messages = messages + [call, obs]
                tool, args, err, usage = self.client.decide(self._system(), messages, self.tools)
                usage["attempt"] = attempt
                usage["after_free_read"] = True
                self.usage.append(usage)
            if err is None:
                err = self.office.validate(tool, args)
            if err is None:
                self.calls += 1
                self.history.append({"kind": "call", "id": f"call_{self.id}_{self.calls}", "tool": tool, "args": args})
                return tool, args
            messages = messages + [{"kind": "note", "role": "user", "text": f"That was not a valid action: {err} {ONE_TOOL}"}]
        self.last_error = err
        self.history.append({"kind": "note", "role": "assistant", "text": "(no valid action)"})
        return None

    def write_diary(self, day):
        text, usage = self.client.complete(DIARY_REQUEST, purpose="diary", system=self._system(), messages=self.history,
                                           max_tokens=DIARY_MAX_TOKENS, timeout=DIARY_TIMEOUT)
        self.usage.append(usage)
        return (text or "").strip()[:DIARY_MAX_CHARS]

    def pop_usage(self):
        out, self.usage = self.usage, []
        return out


def llm_factory(client):
    return lambda emp_id, name, role, office: LLMEmployee(emp_id, name, role, office, client)
