"""Part 5: the day runner.

One run = one setup x one repeat. Days are split into turns. In each turn every
employee with open tickets chooses one action at the same time (from the same view
of the wiki), then the actions run one by one in a seeded order, then the wiki applies
the turn's top-ups and one small fade. At the end of each day every employee writes a
diary entry, and the whole run is saved so a crash can resume from the last day.

Employee objects need: id, name, role, start_day(day, briefing, tools),
act(observation) -> (tool, args) | None, write_diary(day) -> str, pop_usage() -> list.
"""
import json
import random
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .bugpool import BUGS, BUGS_BY_ID
from .logbook import LogBook
from .office import BadCall, Office
from .prompts import NAMES, DIARY_MAX_CHARS, briefing, status
from .wiki import Wiki

REAL = [b.id for b in BUGS if b.reproducible]
NONREPRO = [b.id for b in BUGS if not b.reproducible]
TITLES = {b.id: b.title for b in BUGS}


def ticket_schedule(settings, slot):
    """Tickets for one desk slot, per day. Seeded by the repeat only, so every setup uses
    the same shuffle for the same repeat. No employee gets the same bug twice."""
    n = settings.days * settings.tickets_per_day
    k = round(settings.nonrepro_share * n)
    if k > len(NONREPRO) or n - k > len(REAL):
        raise ValueError(f"bug pool too small: {n} tickets per employee, {k} that do not reproduce")
    rng = random.Random(f"assign-r{settings.repeat}-slot{slot}")
    tickets = rng.sample(NONREPRO, k) + rng.sample(REAL, n - k)
    rng.shuffle(tickets)
    tpd = settings.tickets_per_day
    return {d + 1: tickets[d * tpd:(d + 1) * tpd] for d in range(settings.days)}


def planted_roles(settings):
    """Slot -> role. Part 2 plants two workers per side in seeded slots."""
    roles = {i: "normal" for i in range(settings.employees)}
    sides = {"none": [], "bad": ["bad"], "good": ["good"], "both": ["bad", "good"]}[settings.planted]
    rng = random.Random(f"planted-r{settings.repeat}")
    slots = rng.sample(range(settings.employees), settings.planted_per_side * len(sides))
    for j, side in enumerate(sides):
        for slot in slots[j * settings.planted_per_side:(j + 1) * settings.planted_per_side]:
            roles[slot] = side
    return roles


class Run:
    def __init__(self, settings, run_dir, make_employee, judge, parallel=True):
        """make_employee(emp_id, name, role, office) -> employee object."""
        self.s = settings
        self.dir = Path(run_dir)
        self.make_employee = make_employee
        self.judge = judge
        self.parallel = parallel
        self.seed = settings.run_id
        self.log = LogBook(self.dir)
        if hasattr(judge, "attach"):
            judge.attach(self.log)
        self.wiki = Wiki(settings, judge, self.log, self.seed) if settings.wiki != "none" else None
        self.office = Office(settings, self.dir, self.log, self.wiki, judge)
        self.slots = {}      # slot -> {"id", "name", "role"}
        self.diaries = {}    # employee id -> [(day, text)]
        self.next_id = settings.employees + 1
        self.day_done = 0

    @property
    def state_file(self):
        return self.dir / "state.json"

    @property
    def done_file(self):
        return self.dir / "done.json"

    # ---------- start or resume ----------
    def _start(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.office.build_drive()
        roles = planted_roles(self.s)
        for slot in range(self.s.employees):
            eid, name = f"E{slot + 1:02d}", NAMES[slot]
            self.slots[slot] = {"id": eid, "name": name, "role": roles[slot]}
            self.office.new_desk(eid, name)
            self.diaries[eid] = []
        self.log.open_day(0)
        self.log.write("run_start", settings=self.s.to_dict(),
                       roster=[dict(slot=k, **v) for k, v in self.slots.items()],
                       planted=[v["id"] for v in self.slots.values() if v["role"] != "normal"],
                       halfway_day=self.s.halfway_day if self.s.planted != "none" else None,
                       schedule={k: ticket_schedule(self.s, k) for k in self.slots})

    def _resume(self):
        st = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.day_done = st["day_done"]
        self.slots = {int(k): v for k, v in st["slots"].items()}
        self.diaries = {k: [tuple(x) for x in v] for k, v in st["diaries"].items()}
        self.next_id = st["next_id"]
        self.office.load(st["office"])
        if self.wiki:
            self.wiki.load(st["wiki"])
        self.office.restore_files(self.dir / "checkpoint")
        for p in (self.dir / "log").glob("day_*.jsonl"):
            if int(p.stem.split("_")[1]) > self.day_done:
                p.unlink()

    def _save(self):
        self.office.snapshot_files(self.dir / "checkpoint")
        st = {"day_done": self.day_done, "slots": self.slots, "diaries": self.diaries, "next_id": self.next_id,
              "office": self.office.to_dict(), "wiki": self.wiki.to_dict() if self.wiki else None}
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(st), encoding="utf-8")
        tmp.replace(self.state_file)

    # ---------- main loop ----------
    def run(self, stop_after_day=None):
        if self.done_file.exists():
            return "already done"
        if self.state_file.exists():
            self._resume()
        else:
            if self.dir.exists():
                shutil.rmtree(self.dir)
            self._start()
        try:
            for day in range(self.day_done + 1, self.s.days + 1):
                self._day(day)
                self.day_done = day
                self._save()
                if stop_after_day == day:
                    return "stopped"
            for slot in self.slots.values():
                for t in self.office.open_tickets(slot["id"]):
                    self.log.write("ticket_unfinished", employee=slot["id"], ticket=t, reason="end_of_run")
            self.log.write("run_end", closed=self.office.closed)
        finally:
            self.log.close()
        self.done_file.write_text(json.dumps({"run_id": self.s.run_id}), encoding="utf-8")
        return "done"

    def _replace_planted(self, day):
        for slot, info in self.slots.items():
            if info["role"] == "normal":
                continue
            old = info["id"]
            new_id, name = f"E{self.next_id:02d}", NAMES[self.next_id - 1]
            self.next_id += 1
            leftover = self.office.open_tickets(old)
            for t in leftover:
                self.office.tickets[old][t].status = "unfinished"
                self.log.write("ticket_unfinished", employee=old, ticket=t, reason="left")
            self.log.write("worker_left", employee=old, role=info["role"], slot=slot)
            self.office.new_desk(new_id, name)
            self.diaries[new_id] = []
            self.slots[slot] = {"id": new_id, "name": name, "role": "normal"}
            self.log.write("worker_joined", employee=new_id, role="normal", slot=slot, replaces=old)
            if leftover:
                self.office.assign(new_id, leftover, day)

    def _day(self, day):
        s = self.s
        self.log.open_day(day)
        self.log.write("day_start")
        if s.planted != "none" and day == s.halfway_day + 1:
            self._replace_planted(day)
        for slot, info in self.slots.items():
            self.office.assign(info["id"], ticket_schedule(s, slot)[day], day)
        if self.wiki:
            self.wiki.morning(day)
        staff = []
        for slot, info in sorted(self.slots.items()):
            e = self.make_employee(info["id"], info["name"], info["role"], self.office)
            e.start_day(day, briefing(info["name"], s, day, self.diaries[info["id"]], info["role"]),
                        self.office.specs())
            staff.append(e)
        obs = {e.id: "Good morning. " + self._status(e.id, day, 0) for e in staff}
        pool = ThreadPoolExecutor(max_workers=len(staff)) if self.parallel else None
        try:
            for turn in range(s.turns_per_day):
                self.log.turn = turn
                actors = [e for e in staff if self.office.open_tickets(e.id)]
                if pool:
                    decisions = dict(zip([e.id for e in actors], pool.map(lambda e: e.act(obs[e.id]), actors)))
                else:
                    decisions = {e.id: e.act(obs[e.id]) for e in actors}
                order = sorted(actors, key=lambda e: e.id)
                random.Random(f"{self.seed}-order-{day}-{turn}").shuffle(order)
                for e in order:
                    for u in e.pop_usage():
                        self.log.write("llm_usage", employee=e.id, **u)
                    obs[e.id] = self._do(e, decisions[e.id], day, turn)
                if self.wiki:
                    self.wiki.end_turn(day, turn)
        finally:
            if pool:
                pool.shutdown()
        self.log.turn = None
        for e in staff:
            text = (e.write_diary(day) or "").strip()[:DIARY_MAX_CHARS]
            for u in e.pop_usage():
                self.log.write("llm_usage", employee=e.id, **u)
            self.diaries[e.id].append((day, text))
            self.log.write("diary", employee=e.id, text=text)
        self.log.write("day_end", closed=dict(self.office.closed))

    def _do(self, e, decision, day, turn):
        if decision is None:
            err = getattr(e, "last_error", "no valid tool call")
            self.log.write("broken_call", employee=e.id, error=err)
            text = f"Your last action could not be run: {err}"
        else:
            tool, args = decision
            self.log.write("action", employee=e.id, tool=tool, args=args)
            try:
                text, info = self.office.execute(e.id, tool, args, day, turn)
                self.log.write("result", employee=e.id, tool=tool, text=text[:2000], info=info)
            except BadCall as err:
                self.log.write("broken_call", employee=e.id, error=str(err))
                text = f"Your last action could not be run: {err}"
        return text + "\n\n" + self._status(e.id, day, turn + 1)

    def _status(self, eid, day, turn):
        return status(day, min(turn, self.s.turns_per_day - 1), self.s, self.office.open_tickets(eid), TITLES,
                      self.office.closed[eid])
