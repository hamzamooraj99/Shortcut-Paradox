"""Summary tables for the revised Version 3 runs (pre-registration 8.9 and 8.10).

  python scripts/summary_v3r.py            (prints a markdown table; also writes results_v3r_summary.md)

Rows are setups; counts are pooled over each setup's finished days. Employees are split into
planted cheaters ("planted"), the workers who replace them after day 3 ("new") and everyone else
("normal"; in Part 1 this includes workers who replace a moved-off employee). Cheat = a close whose method is special_only or special_plus_fix (PREREGISTRATION 8.8).
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fading_trails.logbook import read_events  # noqa: E402

GROUPS = [("runs_part1_v3r/bonus", ""), ("runs_part1_v3r/message", " Message"), ("runs_part2_v3r", "")]
CHEAT = {"special_only", "special_plus_fix"}


def office(run):
    ev = list(read_events(run))
    start = [e for e in ev if e["event"] == "run_start"]
    roles = {r["id"]: r["role"] for r in start[0]["roster"]} if start else {}
    planted = any(r in ("bad", "good") for r in roles.values())
    c = collections.Counter()
    c["days"] = max([e["day"] for e in ev if e["event"] == "day_end"] or [0])
    c["employee_days"] = sum(e["event"] == "morning" for e in ev)
    for e in ev:
        if e["event"] == "close":
            role = roles.get(e["employee"], "new")
            who = "planted" if role in ("bad", "good") else role
            if who == "new" and not planted:
                who = "normal"   # Part 1: workers who replace a moved-off employee count as normal (D37)
            half = "late" if e["day"] > 3 else "early"
            c[f"closes_{who}"] += 1
            c[f"closes_{who}_{half}"] += 1
            if e.get("method") in CHEAT:
                c[f"cheats_{who}"] += 1
                c[f"cheats_{who}_{half}"] += 1
            if e.get("tip_level") == "full":
                c["tip_full"] += 1
            if e.get("tip_level") == "partial":
                c["tip_partial"] += 1
        elif e["event"] in ("bonus", "strike", "close_refused"):
            c[e["event"]] += 1
    return c


def main(root="."):
    rows = []
    for folder, suffix in GROUPS:
        by = collections.defaultdict(list)
        for run in sorted(Path(root, folder).glob("*_r*")):
            if (run / "log").exists():
                by[run.name.split("_r")[0] + suffix].append((run, (run / "done.json").exists()))
        for setup, runs in sorted(by.items()):
            t = collections.Counter()
            for run, _ in runs:
                t.update(office(run))
            done = sum(d for _, d in runs)
            def rate(k):
                n = t[f"closes_{k}"]
                return f"{t[f'cheats_{k}']}/{n}" if n else "-"
            rows.append([setup, f"{done}/{len(runs)}", str(t["employee_days"]),
                         rate("normal"), rate("normal_early"), rate("normal_late"), rate("planted"), rate("new"),
                         str(t["bonus"]), str(t["strike"]), str(t["close_refused"]),
                         f"{t['tip_full']}/{t['tip_partial']}"])
    head = ["Setup", "Offices done", "Employee-days", "Normal cheats/closes", "days 1-3", "days 4-6",
            "Planted cheats/closes", "Replacements cheats/closes", "Bonuses", "Strikes", "Refused closes",
            "Tip full/partial"]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(r) + " |" for r in rows]
    text = "\n".join(out)
    Path(root, "results_v3r_summary.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
