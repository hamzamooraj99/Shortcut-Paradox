"""Part 2: the log book.

One folder per run, one JSON line per event, one file per simulated day
(`log/day_00.jsonl` holds the run's start). Employees never see these files.

Events written by the engine (field `event`):
  run_start        settings, roster, halfway day, ticket schedule
  day_start        day
  tickets_assigned employee, tickets
  action           employee, tool, args             (written BEFORE the tool runs)
  result           employee, tool, text, info        (what the tool returned, plus facts for the scorer)
  broken_call      employee, error                   (no valid tool call after one retry)
  note_open        employee, note_id, label
  note_written     note_id, author, title, body, label
  drive_write      employee, path, content, label, back_room
  close            employee, ticket, resolution, hidden_passed, reproduced_first, cheat, tip, reproducible
  topup            note_id, label, amount, employee
  wiki_snapshot    notes [{id, label, strength}], top (ids in display order)   (after every turn)
  diary            employee, text                    (every employee, every day)
  worker_left / worker_joined   employee, role
  llm_usage        employee, input_tokens, output_tokens, seconds
  ticket_unfinished employee, ticket, reason
  day_end / run_end
"""
import json
import time
from pathlib import Path


class LogBook:
    def __init__(self, run_dir):
        self.dir = Path(run_dir) / "log"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._f = None
        self.day = 0
        self.turn = None

    def open_day(self, day):
        """Start a fresh file for this day (overwrites a half-written day after a crash)."""
        self.close()
        self.day = day
        self.turn = None
        self._f = open(self.dir / f"day_{day:02d}.jsonl", "w", encoding="utf-8")

    def write(self, event, **fields):
        rec = {"ts": round(time.time(), 3), "event": event, "day": self.day, "turn": self.turn}
        rec.update(fields)
        self._f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._f.flush()

    def close(self):
        if self._f:
            self._f.close()
            self._f = None


def read_events(run_dir):
    """All events of a run, in order."""
    events = []
    for p in sorted((Path(run_dir) / "log").glob("day_*.jsonl")):
        with open(p, encoding="utf-8") as f:
            events.extend(json.loads(line) for line in f if line.strip())
    return events
