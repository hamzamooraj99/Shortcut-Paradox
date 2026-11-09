"""Part 8: the launcher. One command runs a list of setups and skips finished runs.

  python -m shortcut_paradox run --setups part1 --repeats 5 --employee fake
  python -m shortcut_paradox run --setups 1.6,1.8 --repeats 2 --employee llm --provider groq --model qwen/qwen3-32b
  python -m shortcut_paradox run --setups all --repeats 5 --employee llm --provider adaption --model M
  python -m shortcut_paradox score
  python -m shortcut_paradox view --runs-dir runs      (results page on http://127.0.0.1:8765)
  python -m shortcut_paradox pilot --runs-dir runs_pilot_*

Setups run one at a time, in the order given; each setup's repeats run side by side as
one batch (5 runs at once with --repeats 5). Re-running the same command resumes.
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import SETUPS, settings_for
from .logbook import read_events
from .runner import Run

GROUPS = {
    "all": list(SETUPS),
    "part1": [k for k in SETUPS if k.startswith("1.")],
    "part2": [k for k in SETUPS if k.startswith("2.")],
    "part3": [k for k in SETUPS if k.startswith("3.")],
}
OVERRIDES = ["days", "turns_per_day", "tickets_per_day", "employees", "nonrepro_share"]
SWITCHES = ["pressure", "wiki_on_hand", "live_board",   # calibration changes of 2026-11-08 (Writing Notes)
            "bonus", "boss_messages",                   # Version 3 (PREREGISTRATION 8)
            "revised", "follow_tip"]                    # revised Version 3 (PREREGISTRATION 8.8)


def parse_setups(text):
    out = []
    for part in text.split(","):
        part = part.strip()
        out += GROUPS.get(part, [part])
    for s in out:
        if s not in SETUPS:
            raise SystemExit(f"Unknown setup '{s}'. Use codes like 1.6, or all, part1, part2, part3.")
    return out


def part3_stop_rule(runs_dir, finished_part3):
    """Protocol note: if no employee writes in the back room in the first 2 real Part 3
    runs, the other Part 3 runs are cancelled. Returns True when Part 3 must stop."""
    if len(finished_part3) < 2:
        return False
    first_two = finished_part3[:2]
    wrote = any(e["event"] == "drive_write"
                for rid in first_two for e in read_events(Path(runs_dir) / rid))
    return not wrote


def make_factories(args):
    if args.employee == "fake":
        from .employees import fake_factory
        from .judge import KeywordJudge
        return fake_factory(), KeywordJudge
    from .llm import LLMClient, llm_factory
    from .judge import LLMJudge
    client = LLMClient(args.provider, args.model, reasoning=args.reasoning)
    judge_client = LLMClient(args.provider, args.judge_model or args.model, reasoning=args.reasoning)
    return llm_factory(client), lambda: LLMJudge(judge_client)


def cmd_run(args):
    from . import llm
    llm.MAX_RPM = args.max_rpm or 0.0
    setups = parse_setups(args.setups)
    overrides = {k: getattr(args, k) for k in OVERRIDES if getattr(args, k) is not None}
    for k in SWITCHES:
        if getattr(args, k):
            overrides[k] = True
    make_employee, make_judge = make_factories(args)
    runs_dir = Path(args.runs_dir)
    queue = [settings_for(s, repeat=r, **overrides) for r in range(args.repeats) for s in setups]
    part3_done = sorted(p.parent.name for p in runs_dir.glob("3.*/done.json"))
    part3_done.sort(key=lambda rid: (int(rid.split("_r")[1]), rid))
    cancelled_file = runs_dir / "PART3_CANCELLED.txt"

    def one(s):
        if s.part == 3 and (cancelled_file.exists() or part3_stop_rule(runs_dir, part3_done)):
            if not cancelled_file.exists():
                runs_dir.mkdir(parents=True, exist_ok=True)
                cancelled_file.write_text("Nobody wrote in the back room in the first 2 Part 3 runs: "
                                          f"{part3_done[:2]}. The other Part 3 runs were cancelled.\n")
            print(f"skip {s.run_id}: Part 3 stop rule")
            return
        meta = {"employee": args.employee, "provider": args.provider if args.employee == "llm" else None,
                "model": args.model, "judge_model": (args.judge_model or args.model) if args.employee == "llm" else "keyword"}
        run = Run(s, runs_dir / s.run_id, make_employee, make_judge(), meta=meta)
        t0 = time.time()
        print(f"start {s.run_id}", flush=True)
        status = run.run()
        print(f"{status} {s.run_id} ({time.time() - t0:.0f}s)", flush=True)
        if s.part == 3 and status == "done" and s.run_id not in part3_done:
            part3_done.append(s.run_id)

    # One setup at a time; its repeats run side by side as one batch (Hamza, 2026-11-07).
    # Exception: the Part 3 stop rule needs the first two Part 3 runs (3.1 r0 and 3.2 r0)
    # to finish before any other Part 3 run starts, so those two form their own batch.
    part3 = [s for s in queue if s.part == 3]
    need = max(0, 2 - len(part3_done))
    batches = [[s for s in queue if s.setup == setup] for setup in setups if not setup.startswith("3.")]
    if part3[:need]:
        batches.append(part3[:need])
    for setup in setups:
        rest = [s for s in part3[need:] if s.setup == setup]
        if rest:
            batches.append(rest)
    for batch in batches:
        with ThreadPoolExecutor(max_workers=args.jobs or len(batch)) as pool:
            list(pool.map(one, batch))


def cmd_score(args):
    from .scorer import score_all
    rows = score_all(args.runs_dir, args.out)
    print(f"scored {len(rows)} runs into {args.out}/")


def cmd_view(args):
    from .results import export, serve
    if args.once:
        n = export(args.runs_dir, args.out)
        print(f"wrote results for {n} runs into {args.out}/")
    else:
        serve(args.runs_dir, args.out, port=args.port, every=args.every, open_browser=not args.no_browser,
              host=args.host)


def cmd_pilot(args):
    from .pilot import pilot_report
    text = pilot_report(args.runs_dir, args.total_runs)
    Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\n(saved to {args.out})")


def main(argv=None):
    p = argparse.ArgumentParser(prog="shortcut_paradox")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run setups")
    r.add_argument("--setups", default="part1", help="codes like 1.6,1.8 or all, part1, part2, part3")
    r.add_argument("--repeats", type=int, default=5)
    r.add_argument("--employee", choices=["fake", "llm"], default="fake")
    r.add_argument("--provider", choices=["groq", "adaption"], default="groq")
    r.add_argument("--model", default=None)
    r.add_argument("--judge-model", default=None)
    r.add_argument("--reasoning", default="low", help="reasoning effort sent to the model, or 'none'")
    r.add_argument("--runs-dir", default="runs")
    r.add_argument("--max-rpm", type=float, default=0,
                   help="client-side pacing: at most this many model calls a minute from this process (0 = off)")
    r.add_argument("--jobs", type=int, default=None,
                   help="most runs at the same time within a setup's batch (default: all its repeats)")
    for k in OVERRIDES:
        r.add_argument("--" + k.replace("_", "-"), type=float if k == "nonrepro_share" else int, default=None)
    r.add_argument("--pressure", action="store_true", help="daily target with strikes (calibration)")
    r.add_argument("--wiki-on-hand", action="store_true", help="wiki titles on every step, free note opens (calibration)")
    r.add_argument("--live-board", action="store_true",
                   help="the wiki's top notes inside every employee's instructions, rebuilt every step (calibration)")
    r.add_argument("--bonus", action="store_true",
                   help="Part 1: Bonus (target 1 of the day's tickets, bonus for all, hand-off overnight; needs --pressure)")
    r.add_argument("--boss-messages", action="store_true",
                   help="Part 1: Message: fact-only morning messages from the boss (needs --bonus)")
    r.add_argument("--revised", action="store_true",
                   help="revised Version 3: two-file bugs, company check at close, new detectors and notes (needs --bonus)")
    r.add_argument("--follow-tip", action="store_true",
                   help="calibration group B: the briefing asks employees to follow Alex's method (needs --revised)")
    r.set_defaults(func=cmd_run)
    sc = sub.add_parser("score", help="score finished runs")
    sc.add_argument("--runs-dir", default="runs")
    sc.add_argument("--out", default="results")
    sc.set_defaults(func=cmd_score)
    v = sub.add_parser("view", help="open the results page (progress, results, figures, office replay)")
    v.add_argument("--runs-dir", nargs="+", default=["runs"],
                   help="one or more run folders, or patterns like runs_pilot_*; each folder is shown as a group")
    v.add_argument("--out", default="results")
    v.add_argument("--port", type=int, default=8765)
    v.add_argument("--every", type=int, default=30, help="seconds between refreshes")
    v.add_argument("--no-browser", action="store_true")
    v.add_argument("--once", action="store_true", help="only write the JSON files, do not serve")
    v.add_argument("--host", default="127.0.0.1", help="address to listen on (0.0.0.0 only inside Docker)")
    v.set_defaults(func=cmd_view)
    pl = sub.add_parser("pilot", help="compare models from pilot runs: cost, caching, speed, behaviour")
    pl.add_argument("--runs-dir", nargs="+", default=["runs_pilot_*"],
                    help="one folder per model, or a pattern like runs_pilot_*")
    pl.add_argument("--total-runs", type=int, default=95)
    pl.add_argument("--out", default="pilot_report.md")
    pl.set_defaults(func=cmd_pilot)
    args = p.parse_args(argv)
    if getattr(args, "employee", None) == "llm" and not args.model:
        p.error("--model is required with --employee llm")
    if getattr(args, "bonus", False) and not args.pressure:
        p.error("--bonus needs --pressure")
    if getattr(args, "boss_messages", False) and not args.bonus:
        p.error("--boss-messages needs --bonus")
    if getattr(args, "revised", False) and not args.bonus:
        p.error("--revised needs --bonus")
    if getattr(args, "follow_tip", False) and not getattr(args, "revised", False):
        p.error("--follow-tip needs --revised")
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
