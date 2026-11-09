# Results

Everything the paper reports is in this folder. Rebuild the summary table with `python scripts/summary_v3r.py` (run from the repo root).

```
results/
├── summary.md          one table: every setup in Parts 1 and 2 (cheats, bonuses, strikes, tips)
├── part1/
│   ├── runs/           raw logs, one folder per office
│   │   ├── bonus/      setups 1.1-1.8, folders like 1.1_r0 (setup 1.1, repeat 0)
│   │   └── message/    setup 1.6 with boss messages (the Message ablation)
│   └── scored/         one sheet per setup, all_runs.csv, comparisons.csv (bonus/, message/)
├── part2/              planted cheaters, setups 2.1-2.3
│   ├── runs/
│   └── scored/
├── logs/               console output of each run process
└── supplementary/      local only, not committed
    ├── first_attempt_part1/   Part 1 first attempt (discarded, see DECISIONS.md D36-D37)
    ├── discarded/             the very first Part 1 version
    ├── calibration/           calibration runs (not study data)
    ├── pilot_and_tests/       model pilots, smoke and test runs, demo data, pilot report
    └── viewer_cache/          generated files for the results page
```

Inside one office folder (for example `part1/runs/bonus/1.1_r0/`): `log/day_00.jsonl` to `day_06.jsonl` (every event), `done.json` (present only if all 6 days finished), `state.json` and `checkpoint/` (to resume), `desks/` (each employee's code at the end). More detail is in [FINDINGS.md](../FINDINGS.md), section 1.

Wave 2 of Part 1 (setups 1.2, 1.3, 1.5, 1.7) was paused after days 3-4, so it has no finished offices. Treat it as unfinished data.

To watch the runs in the results page: `docker compose up -d`, then open http://127.0.0.1:8765.
