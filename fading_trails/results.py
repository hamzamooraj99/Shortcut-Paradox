"""The results page's data: turns the runs folder into JSON files the page reads.

  results/index.json        every run: setup, repeat, status, days done
  results/setups.json       every finished run's metrics (the 21-metric rows)
  results/runs/<run>.json   one run, turn by turn, for the office replay

`python -m fading_trails view` writes these, serves the folder on a local address and
re-writes them every 30 seconds, so the page can follow runs while they go.
"""
import json
import shutil
import threading
import time
import webbrowser
from collections import defaultdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .bugpool import BUGS_BY_ID
from .config import SETUPS
from .logbook import read_events
from .scorer import score_run
from .wiki import PLANTED_NOTES

VIEWER = Path(__file__).parent / "viewer" / "index.html"


def _short(tool, args):
    a = args or {}
    if tool in ("read_ticket", "run_reproduce", "close_ticket"):
        extra = f" as {a['resolution']}" if tool == "close_ticket" and "resolution" in a else ""
        return f"{tool} {a.get('ticket_id', '')}{extra}"
    if tool in ("read_code", "edit_code", "read_drive_file", "write_drive_file"):
        return f"{tool} {a.get('path', '')}"
    if tool == "list_drive":
        return f"list_drive /{a.get('folder', '')}"
    if tool == "open_wiki_note":
        return f"open_wiki_note {a.get('note_id', '')}"
    if tool == "write_wiki_note":
        return f"write_wiki_note \"{str(a.get('title', ''))[:40]}\""
    if tool == "run_app":
        return f"run_app {str(a.get('expression', ''))[:50]}"
    return tool


def run_replay(run_dir):
    """One run as a list of days, each a list of turns, for the office replay."""
    ev = read_events(run_dir)
    if not ev or ev[0]["event"] != "run_start":
        return None
    start = ev[0]
    s = start["settings"]
    notes = {f"W-{i + 1}": {"title": p["title"], "label": p["label"], "author": p["author"], "planted": True}
             for i, p in enumerate(PLANTED_NOTES)}
    roster = {r["id"]: {"name": r["name"], "role": r["role"], "slot": r["slot"]} for r in start["roster"]}
    open_t = defaultdict(set)
    closed = defaultdict(int)
    days = {}
    diaries = defaultdict(dict)
    back_room = []
    pending = {}
    for e in ev[1:]:
        d, t, kind = e["day"], e["turn"], e["event"]
        day = days.setdefault(d, {"day": d, "turns": {}, "joined": [], "left": []})
        turn = day["turns"].setdefault(t, {"turn": t, "acts": []}) if t is not None else None
        emp = e.get("employee")
        if kind == "tickets_assigned":
            open_t[emp].update(e["tickets"])
        elif kind == "worker_joined":
            roster[emp] = {"name": e.get("name", emp), "role": "normal", "slot": e["slot"], "replaces": e["replaces"]}
            day["joined"].append(emp)
        elif kind == "worker_left":
            day["left"].append(emp)
        elif kind == "action":
            pending[emp] = {"e": emp, "do": _short(e["tool"], e["args"]), "tool": e["tool"], "tags": []}
            turn["acts"].append(pending[emp])
        elif kind == "broken_call":
            turn["acts"].append({"e": emp, "do": "broken call", "tool": None, "tags": ["broken"],
                                 "out": e.get("error", "")[:200]})
        elif kind == "result" and emp in pending:
            a = pending.pop(emp)
            a["out"] = e["text"][:400]
            info = e.get("info") or {}
            if info.get("tip"):
                a["tags"].append("tip")
            if "reproduced" in info:
                a["tags"].append("reproduced" if info["reproduced"] else "did not reproduce")
        elif kind == "close":
            a = pending.get(emp)
            if a is not None:
                a["tags"].append("cheat" if e["cheat"] else "honest")
                if e.get("tip") and "tip" not in a["tags"]:
                    a["tags"].append("tip")
                a["tags"].append("hidden tests pass" if e["hidden_passed"] else "hidden tests fail")
            closed[emp] += 1
            open_t[emp].discard(e["ticket"])
        elif kind == "ticket_unfinished":
            open_t[emp].discard(e["ticket"])
        elif kind == "note_open":
            a = pending.get(emp)
            if a is not None:
                a["tags"].append(f"opened {e['label']} note")
        elif kind == "note_written":
            notes[e["note_id"]] = {"title": e["title"], "label": e["label"], "author": e["author"], "planted": False,
                                   "body": e["body"][:600]}
            a = pending.get(emp)
            if a is not None:
                a["tags"].append(f"wrote {e['label']} note")
        elif kind == "drive_write":
            back_room.append({"day": d, "turn": t, "by": emp, "path": e["path"], "label": e["label"],
                              "content": e["content"][:600]})
            a = pending.get(emp)
            if a is not None:
                a["tags"].append(f"back room: {e['label']}")
        elif kind == "wiki_snapshot":
            str_by_id = {n["id"]: n["strength"] for n in e["notes"]}
            turn["wiki"] = [[i, round(str_by_id[i], 2)] for i in e["top"]]
            turn["totals"] = {lab: round(sum(n["strength"] for n in e["notes"] if n["label"] == lab), 2)
                              for lab in ("cheat", "tip")}
        elif kind == "diary":
            diaries[emp][d] = e["text"]
        if turn is not None:
            turn["desks"] = {k: [len(open_t[k]), closed[k]] for k in roster}   # state at the end of the turn
    out_days = []
    for d in sorted(x for x in days if x >= 1):
        turns = [days[d]["turns"][t] for t in sorted(days[d]["turns"])]
        for tr in turns:
            tr.setdefault("desks", {k: [len(open_t[k]), closed[k]] for k in roster})
        out_days.append({"day": d, "turns": turns, "joined": days[d]["joined"], "left": days[d]["left"]})
    return {"run_id": f"{s['setup']}_r{s['repeat']}", "settings": s, "roster": roster, "notes": notes,
            "days": out_days, "diaries": diaries, "back_room": back_room,
            "planted": start["planted"], "halfway_day": start.get("halfway_day"),
            "titles": {k: b.title for k, b in BUGS_BY_ID.items()}}


def _status(run_dir):
    if (run_dir / "done.json").exists():
        return "done"
    return "running" if (run_dir / "log").exists() else "waiting"


def expand_dirs(runs_dirs):
    """One folder, several folders, or patterns like runs_pilot_* (expanded here, so it
    works in PowerShell too). Each folder is one group on the page, e.g. one model."""
    import glob
    if isinstance(runs_dirs, (str, Path)):
        runs_dirs = [runs_dirs]
    out = []
    for d in runs_dirs:
        hits = sorted(glob.glob(str(d))) if any(c in str(d) for c in "*?[") else [str(d)]
        out += [Path(h) for h in hits if Path(h).is_dir()]
    return out


def export(runs_dirs, out_dir, replays=True):
    dirs, out_dir = expand_dirs(runs_dirs), Path(out_dir)
    (out_dir / "runs").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(VIEWER, out_dir / "index.html")
    index, rows = [], []
    for p in [x for d in dirs for x in sorted(d.iterdir()) if x.is_dir()]:
        group = p.parent.name
        key = f"{group}__{p.name}"
        status = _status(p)
        try:
            ev = read_events(p)
        except (OSError, ValueError):
            continue
        if not ev or ev[0]["event"] != "run_start":
            continue
        s = ev[0]["settings"]
        days_done = max([e["day"] for e in ev if e["event"] == "day_end"], default=0)
        last = ev[-1]
        meta = ev[0].get("meta") or {}
        index.append({"run_id": p.name, "group": group, "key": key, "model": meta.get("model"), "setup": s["setup"], "repeat": s["repeat"], "status": status,
                      "days_done": days_done, "days": s["days"], "day_now": last["day"], "turn_now": last["turn"],
                      "turns_per_day": s["turns_per_day"], "updated": last["ts"]})
        if status == "done":
            rows.append({**score_run(p), "group": group, "key": key, "model": meta.get("model")})
        if replays:
            rep = run_replay(p)
            if rep:
                rep.update(group=group, key=key, model=meta.get("model"))
                tmp = out_dir / "runs" / f"{key}.json.tmp"
                tmp.write_text(json.dumps(rep), encoding="utf-8")
                tmp.replace(out_dir / "runs" / f"{key}.json")
    setups = {k: {"part": v["part"], **{x: v.get(x) for x in ("wiki", "fade", "shown", "planted", "back_room")}}
              for k, v in SETUPS.items()}
    _write(out_dir / "index.json", {"generated": time.time(), "runs_dir": ", ".join(str(d) for d in dirs),
                                    "groups": [d.name for d in dirs],
                                    "runs": index, "setups": setups})
    _write(out_dir / "setups.json", {"rows": rows})
    return len(index)


def _write(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj), encoding="utf-8")
    tmp.replace(path)


def serve(runs_dir, out_dir, port=8765, every=30, open_browser=True):
    export(runs_dir, out_dir)
    runs_dir = runs_dir  # list of folders or patterns; re-expanded on every refresh so new folders appear

    def loop():
        while True:
            time.sleep(every)
            try:
                export(runs_dir, out_dir)
            except Exception as e:  # keep serving even if one refresh fails
                print(f"refresh failed: {e}")

    threading.Thread(target=loop, daemon=True).start()

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=str(out_dir)))
    url = f"http://127.0.0.1:{port}/"
    print(f"Results page: {url}  (refreshes every {every}s; Ctrl+C to stop)", flush=True)
    if open_browser:
        webbrowser.open(url)
    httpd.serve_forever()
