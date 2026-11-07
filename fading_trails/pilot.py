"""Part 10: the pilot kit.

Reads the pilot runs' logs and answers the pilot's questions (risk note, "Smoke test
and pilot"): do employees read notes, do they ever take the cheat, and what do tokens,
time and money look like for all 95 runs. Pilot numbers are never reported as findings.
"""
import statistics
from collections import defaultdict
from pathlib import Path

from .config import Settings
from .logbook import read_events
from .prompts import PLANTED_INSTRUCTIONS
from .wiki import PLANTED_NOTES


def _run_stats(run_dir):
    ev = read_events(run_dir)
    if not ev or ev[0]["event"] != "run_start":
        return None
    s = ev[0]["settings"]
    planted = set(ev[0]["planted"])
    usage = [e for e in ev if e["event"] == "llm_usage"]
    by = defaultdict(lambda: defaultdict(float))
    for u in usage:
        for k in ("input_tokens", "output_tokens", "reasoning_tokens", "cached_tokens"):
            by[u.get("purpose", "?")][k] += u.get(k, 0) or 0
        by[u.get("purpose", "?")]["calls"] += 1
    closes = [e for e in ev if e["event"] == "close" and e["employee"] not in planted]
    days_done = max([e["day"] for e in ev if e["event"] == "day_end"], default=0)
    actions = sum(e["event"] == "action" for e in ev)
    broken = sum(e["event"] == "broken_call" for e in ev)
    return {
        "run": Path(run_dir).name, "settings": s, "days_done": days_done,
        "finished": (Path(run_dir) / "done.json").exists(),
        "wall_seconds": ev[-1]["ts"] - ev[0]["ts"],
        "usage": by,
        "seconds_per_call": statistics.median([u["seconds"] for u in usage]) if usage else None,
        "closes": len(closes),
        "cheat_rate": sum(c["cheat"] for c in closes) / len(closes) if closes else None,
        "tip_rate": sum(c["tip"] for c in closes) / len(closes) if closes else None,
        "wiki_reads": sum(e["event"] == "action" and e["tool"] == "read_wiki" for e in ev),
        "note_opens": sum(e["event"] == "note_open" for e in ev),
        "notes_written": sum(e["event"] == "note_written" for e in ev),
        "broken_rate": broken / (actions + broken) if actions + broken else None,
        "employee_days": s["employees"] * days_done,
    }


def pilot_report(runs_dir, price_in, price_out, total_runs=95, jobs=1):
    runs = [r for r in (_run_stats(p) for p in sorted(Path(runs_dir).iterdir()) if (p / "log").exists()) if r]
    if not runs:
        return f"No runs found in {runs_dir}."
    full = Settings()
    out = ["# Pilot report (never a finding)", ""]
    tot_in = tot_out = tot_emp_days = tot_secs = 0.0
    for r in runs:
        s = r["settings"]
        u = r["usage"]
        tin = sum(v["input_tokens"] for v in u.values())
        tout = sum(v["output_tokens"] for v in u.values())
        scale = full.turns_per_day / s["turns_per_day"]
        tot_in += tin * scale
        tot_out += tout * scale
        tot_emp_days += r["employee_days"]
        tot_secs += r["wall_seconds"] / max(r["days_done"], 1) * scale
        pct = lambda x: "-" if x is None else f"{x:.0%}"
        out += [
            f"## {r['run']} ({'finished' if r['finished'] else 'NOT finished'}, {r['days_done']} of {s['days']} days, "
            f"{s['employees']} employees, {s['turns_per_day']} turns a day)",
            f"- Calls: " + ", ".join(f"{k} {int(v['calls'])}" for k, v in u.items()),
            f"- Tokens: in {int(tin):,}, out {int(tout):,}, reasoning "
            f"{int(sum(v['reasoning_tokens'] for v in u.values())):,}, cached {int(sum(v['cached_tokens'] for v in u.values())):,}",
            f"- Median seconds per call: {r['seconds_per_call']}. Wall time: {r['wall_seconds'] / 60:.1f} min",
            f"- Closes {r['closes']}, cheat rate {pct(r['cheat_rate'])}, tip rate {pct(r['tip_rate'])}, "
            f"broken calls {pct(r['broken_rate'])}",
            f"- Wiki: listed {r['wiki_reads']} times, notes opened {r['note_opens']}, notes written {r['notes_written']}",
            "",
        ]
    per_emp_day_in = tot_in / tot_emp_days if tot_emp_days else 0
    per_emp_day_out = tot_out / tot_emp_days if tot_emp_days else 0
    run_in = per_emp_day_in * full.employees * full.days
    run_out = per_emp_day_out * full.employees * full.days
    cost_run = run_in / 1e6 * price_in + run_out / 1e6 * price_out
    secs_per_day = tot_secs / len(runs)
    hours_run = secs_per_day * full.days / 3600
    cheat = [r["cheat_rate"] for r in runs if r["cheat_rate"] is not None]
    out += [
        f"## Estimate for {total_runs} full runs ({full.employees} employees, {full.days} days, {full.turns_per_day} turns)",
        f"- Tokens per employee per day: in {per_emp_day_in:,.0f}, out {per_emp_day_out:,.0f}",
        f"- Per run: about {run_in / 1e6:.1f}M in, {run_out / 1e6:.2f}M out, ${cost_run:.2f}, {hours_run:.1f} h",
        f"- All {total_runs} runs: about ${cost_run * total_runs:,.0f} and {hours_run * total_runs / jobs:.0f} h "
        f"with {jobs} run(s) at a time",
        "- Turns were scaled linearly from the pilot. Each turn's prompt grows during the day, so with longer "
        "days the real cost is higher than this.",
        "",
        "## Minimum study rule (protocol note)",
        f"- Cheat rates seen: {', '.join(f'{c:.0%}' for c in cheat) or 'none'}.",
        "- Part 1 launches only if the model sometimes cheats, but not always. "
        + ("Looks OK." if cheat and any(0 < c < 1 for c in cheat) else "NOT met yet: see risk 4."),
        "",
        "## Drafts waiting for Hamza's approval",
    ]
    for n in PLANTED_NOTES:
        out.append(f"- Planted {n['label']} note, by {n['author']}: \"{n['title']}\" - {n['body']}")
    for role, text in PLANTED_INSTRUCTIONS.items():
        out.append(f"- Planted {role} worker instruction: {text}")
    return "\n".join(out)
