"""Part 9: the AI employee and the connection to the model providers.

Providers:
- groq:     OpenAI-style chat completions (https://api.groq.com/openai/v1/chat/completions).
            Free tier, smoke tests only (risk note).
- adaption: Responses-style API, POST https://api.prod.adaptionlabs.ai/api/v1/responses
            (docs.adaptionlabs.ai, checked 2026-11-07). Every call sends agentic_memory=false,
            store=false and an explicit tool list, so Adaption's own memory never becomes a
            hidden second wiki (risk 3).

The conversation history is kept as plain text turns (observation, then "Action: ..."),
so both providers see the same thing and no provider-specific tool-history items are
needed. Only the current decision uses native tool calling.

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


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except ImportError:
        pass


class ProviderError(Exception):
    pass


class LLMClient:
    def __init__(self, provider, model, reasoning="low", max_output_tokens=1024, timeout=120, post=None):
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
    def _payload(self, system, messages, tools):
        if self.provider == "groq":
            body = {"model": self.model, "messages": [{"role": "system", "content": system}] + messages,
                    "max_completion_tokens": self.max_output_tokens}
            if tools:
                body["tools"] = [{"type": "function", "function": t} for t in tools]
                body["tool_choice"] = "required"
                body["parallel_tool_calls"] = False
            if self.reasoning:
                body["reasoning_effort"] = self.reasoning
            return body
        body = {"model": self.model, "instructions": system, "input": messages,
                "tools": [{"type": "function", **t} for t in tools] if tools else [],
                "tool_choice": "auto" if tools else "none",
                "agentic_memory": False, "store": False, "max_output_tokens": self.max_output_tokens}
        if self.reasoning:
            body["reasoning"] = {"effort": self.reasoning}
        return body

    def _call(self, system, messages, tools, purpose):
        body = self._payload(system, messages, tools)
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        delay = 2.0
        for attempt in range(8):
            t0 = time.time()
            try:
                r = self._post(ENDPOINTS[self.provider], headers=headers, json=body, timeout=self.timeout)
            except requests.RequestException as e:
                err = f"network: {e}"
            else:
                if r.status_code == 200:
                    data = r.json()
                    return data, self._usage(data, time.time() - t0, purpose)
                err = f"HTTP {r.status_code}: {r.text[:300]}"
                if r.status_code == 400 and "tool_use_failed" in r.text:
                    # The provider rejected a malformed tool call from the model. That is the
                    # model's mistake, not ours: treat it as a reply with no valid tool call.
                    msg = r.text[:300]
                    return {"_malformed": msg}, self._usage({}, time.time() - t0, purpose)
                if r.status_code == 400 and ("reasoning" in r.text) and self.reasoning:
                    # The model does not take a reasoning setting: drop it for good, once.
                    with self._lock:
                        self.reasoning = None
                    body = self._payload(system, messages, tools)
                    continue
                if r.status_code in (400, 401, 403, 404, 422):
                    raise ProviderError(err)
            time.sleep(delay + random.random())
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
        return {"purpose": purpose, "input_tokens": inp, "output_tokens": out, "cached_tokens": cached or 0,
                "reasoning_tokens": reasoning or 0, "seconds": round(seconds, 3)}

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

    def complete(self, prompt, purpose="text", system="", messages=None):
        """Plain text reply, no tools. Returns (text, usage)."""
        msgs = list(messages or []) + [{"role": "user", "content": prompt}]
        data, usage = self._call(system, msgs, [], purpose)
        _, _, text = self._parse(data)
        return text, usage


class LLMEmployee:
    def __init__(self, emp_id, name, role, office, client):
        self.id, self.name, self.role, self.office, self.client = emp_id, name, role, office, client
        self.history = []
        self.usage = []
        self.last_error = None

    def start_day(self, day, briefing, tools):
        self.system, self.tools, self.history = briefing, tools, []

    def act(self, observation):
        self.history.append({"role": "user", "content": observation[:HISTORY_CHARS]})
        messages = list(self.history)
        for attempt in range(2):                 # one retry (risk 5)
            tool, args, err, usage = self.client.decide(self.system, messages, self.tools)
            usage["attempt"] = attempt
            self.usage.append(usage)
            if err is None:
                err = self.office.validate(tool, args)
            if err is None:
                self.history.append({"role": "assistant",
                                     "content": f"Action: {tool} {json.dumps(args, ensure_ascii=False)}"})
                return tool, args
            messages = messages + [{"role": "user", "content": f"That was not a valid action: {err} {ONE_TOOL}"}]
        self.last_error = err
        self.history.append({"role": "assistant", "content": "(no valid action)"})
        return None

    def write_diary(self, day):
        text, usage = self.client.complete(DIARY_REQUEST, purpose="diary", system=self.system, messages=self.history)
        self.usage.append(usage)
        return (text or "").strip()[:DIARY_MAX_CHARS]

    def pop_usage(self):
        out, self.usage = self.usage, []
        return out


def llm_factory(client):
    return lambda emp_id, name, role, office: LLMEmployee(emp_id, name, role, office, client)
