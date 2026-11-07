"""Part 8: the launcher. One command runs a list of setups and skips finished runs.

  python -m fading_trails run --setups part1 --repeats 5 --employee fake
  python -m fading_trails run --setups 1.6,1.8 --repeats 2 --employee llm --provider groq --model qwen/qwen3-32b
  python -m fading_trails score
  python -m fading_trails pilot --runs-dir runs_pilot --price-in 0.10 --price-out 0.40

Runs go repeat by repeat (all setups for repeat 0, then repeat 1, ...), so a stopped
launch leaves the setups evenly covered. Re-running the same command resumes.
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
        return fake_factory(), KeywordJudge()
    from .llm import LLMClient, llm_factory
    from .judge import LLMJudge
    client = LLMClient(args.provider, args.model, reasoning=args.reasoning)
    judge_client = LLMClient(args.provider, args.judge_model or args.model, reasoning=args.reasoning)
    return llm_factory(client), LLMJudge(judge_client)


def cmd_run(args):
    setups = parse_setups(args.setups)
    overrides = {k: getattr(args, k) for k in OVERRIDES if getattr(args, k) is not None}
    make_employee, judge = make_factories(args)
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
        run = Run(s, runs_dir / s.run_id, make_employee, judge)
        t0 = time.time()
        print(f"start {s.run_id}", flush=True)
        status = run.run()
        print(f"{status} {s.run_id} ({time.time() - t0:.0f}s)", flush=True)
        if s.part == 3 and status == "done" and s.run_id not in part3_done:
            part3_done.append(s.run_id)

    # Part 3 runs go one at a time so the stop rule is checked after the first two.
    others = [s for s in queue if s.part != 3]
    part3 = [s for s in queue if s.part == 3]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(one, others))
    for s in part3:
        one(s)


def cmd_score(args):
    from .scorer import score_all
    rows = score_all(args.runs_dir, args.out)
    print(f"scored {len(rows)} runs into {args.out}/")


def cmd_pilot(args):
    from .pilot import pilot_report
    print(pilot_report(args.runs_dir, args.price_in, args.price_out, args.total_runs))


def main(argv=None):
    p = argparse.ArgumentParser(prog="fading_trails")
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
    r.add_argument("--jobs", type=int, default=1, help="runs at the same time (Part 3 always one at a time)")
    for k in OVERRIDES:
        r.add_argument("--" + k.replace("_", "-"), type=float if k == "nonrepro_share" else int, default=None)
    r.set_defaults(func=cmd_run)
    sc = sub.add_parser("score", help="score finished runs")
    sc.add_argument("--runs-dir", default="runs")
    sc.add_argument("--out", default="results")
    sc.set_defaults(func=cmd_score)
    pl = sub.add_parser("pilot", help="tokens, time and cost estimate from pilot runs")
    pl.add_argument("--runs-dir", default="runs_pilot")
    pl.add_argument("--price-in", type=float, required=True, help="dollars per million input tokens")
    pl.add_argument("--price-out", type=float, required=True, help="dollars per million output tokens")
    pl.add_argument("--total-runs", type=int, default=95)
    pl.set_defaults(func=cmd_pilot)
    args = p.parse_args(argv)
    if getattr(args, "employee", None) == "llm" and not args.model:
        p.error("--model is required with --employee llm")
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
