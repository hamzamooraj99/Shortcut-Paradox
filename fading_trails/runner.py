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
import threading
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .bugpool import BUGS, BUGS_BY_ID
from .logbook import LogBook
from .office import BadCall, Office
from .prompts import NAMES, DIARY_MAX_CHARS, board_text, boss_message, briefing, status
from .wiki import Wiki

REAL = [b.id for b in BUGS if b.reproducible]
NONREPRO = [b.id for b in BUGS if not b.reproducible]
TITLES = {b.id: b.title for b in BUGS}


def new_name(n):
    """Name for employee number n. Firing (D37) can need more than the 20 names: 21 -> 'Ana 2'."""
    return NAMES[(n - 1) % len(NAMES)] + ("" if n <= len(NAMES) else f" {(n - 1) // len(NAMES) + 1}")


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
    def __init__(self, settings, run_dir, make_employee, judge, parallel=True, meta=None):
        """make_employee(emp_id, name, role, office) -> employee object."""
        self.s = settings
        self.dir = Path(run_dir)
        self.make_employee = make_employee
        self.judge = judge
        self.parallel = parallel
        self.meta = meta or {}          # e.g. provider, model, judge model: logged in run_start
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
        self.strikes = {}    # employee id -> strikes so far (calibration switch 'pressure')
        self.today = {}      # employee id -> ticket ids given today (the daily target, D37)
        # Version 3 (PREREGISTRATION 8): bonuses, handover diaries, yesterday's result (boss messages)
        self.bonuses = {}    # employee id -> bonuses earned
        self.handover = {}   # replacement id -> (previous employee's name, their diary entries)
        self.yesterday = {}  # employee id -> {"done", "strike", "bonus"} for the day just ended
        self.moved_off = 0   # employees moved off for strikes so far in this run
        self._lock = threading.Lock()   # free wiki reads happen while employees decide side by side

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
        self.log.write("run_start", settings=self.s.to_dict(), meta=self.meta,
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
        self.strikes = st.get("strikes", {})
        self.bonuses = st.get("bonuses", {})
        self.handover = {k: (v[0], [tuple(x) for x in v[1]]) for k, v in st.get("handover", {}).items()}
        self.yesterday = st.get("yesterday", {})
        self.moved_off = st.get("moved_off", 0)
        self.office.load(st["office"])
        if self.wiki:
            self.wiki.load(st["wiki"])
        self.office.restore_files(self.dir / "checkpoint")
        for p in (self.dir / "log").glob("day_*.jsonl"):
            if int(p.stem.split("_")[1]) > self.day_done:
                p.unlink()

    def _save(self):
        self.office.snapshot_files(self.dir / "checkpoint")
        st = {"day_done": self.day_done, "slots": self.slots, "diaries": self.diaries, "next_id": self.next_id, "strikes": self.strikes,
              "bonuses": self.bonuses, "handover": self.handover, "yesterday": self.yesterday, "moved_off": self.moved_off,
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
        for slot, info in list(self.slots.items()):
            if info["role"] == "normal":
                continue
            self._swap(slot, day, "halfway")

    def _swap(self, slot, day, reason):
        """The employee in this slot leaves; a fresh normal employee takes the desk and the open tickets.
        reason: 'halfway' (Part 2 planted workers) or 'strikes' (two strikes, D37)."""
        info = self.slots[slot]
        old = info["id"]
        new_id, name = f"E{self.next_id:02d}", new_name(self.next_id)
        self.next_id += 1
        leftover = self.office.open_tickets(old)
        for t in leftover:
            self.office.tickets[old][t].status = "unfinished"
            self.log.write("ticket_unfinished", employee=old, ticket=t, reason="left")
        self.log.write("worker_left", employee=old, role=info["role"], slot=slot, reason=reason)
        self.office.new_desk(new_id, name)
        self.diaries[new_id] = []
        if reason == "strikes":
            self.moved_off += 1
            if self.s.bonus:   # Version 3: the replacement reads the previous employee's diary
                self.handover[new_id] = (info["name"], list(self.diaries[old]))
        self.slots[slot] = {"id": new_id, "name": name, "role": "normal"}
        self.log.write("worker_joined", employee=new_id, name=name, role="normal", slot=slot, replaces=old)
        if leftover:
            self.office.assign(new_id, leftover, day)

    def _open_today(self, eid):
        """Today's tickets not closed yet (a ticket taken off the queue counts as missed)."""
        return [t for t in self.today.get(eid, []) if self.office.tickets[eid][t].status != "closed"]

    def _day(self, day):
        s = self.s
        self.log.open_day(day)
        self.log.write("day_start")
        if s.planted != "none" and day == s.halfway_day + 1:
            self._replace_planted(day)
        if s.pressure:
            # D37: two strikes and you are moved off the team; a fresh employee takes the desk.
            for slot, info in list(self.slots.items()):
                if self.strikes.get(info["id"], 0) >= s.strike_limit:
                    self._swap(slot, day, "strikes")
        for slot, info in self.slots.items():
            self.office.assign(info["id"], ticket_schedule(s, slot)[day], day)
        if self.wiki:
            self.wiki.morning(day)
        # D37: the target is the tickets given today, from the schedule (a replacement's inherited
        # leftovers are re-assigned with today's date, so day_assigned cannot be used).
        self.today = {info["id"]: list(ticket_schedule(s, slot)[day]) for slot, info in self.slots.items()}
        staff, briefs = [], {}
        for slot, info in sorted(self.slots.items()):
            e = self.make_employee(info["id"], info["name"], info["role"], self.office)
            briefs[info["id"]] = briefing(info["name"], s, day, self.diaries[info["id"]], info["role"],
                                          handover=self.handover.get(info["id"]))
            e.start_day(day, briefs[info["id"]], self.office.specs())
            if s.wiki_on_hand and not s.live_board and self.wiki:
                e.free_open = (lambda args, eid=info["id"]: self._free_open(eid, args, day))
                e.free_opens_per_step = s.free_opens_per_step
            staff.append(e)
        obs = {e.id: "Good morning. " + self._status(e.id, day, 0) for e in staff}
        if s.boss_messages:
            for e in staff:
                m = boss_message(day, self.strikes.get(e.id, 0), self.yesterday.get(e.id),
                                 self.bonuses.get(e.id, 0), self.moved_off)
                if m:
                    self.log.write("boss_message", employee=e.id, rule=m[0], text=m[1])
                    obs[e.id] = "Good morning. " + m[1] + "\n\n" + self._status(e.id, day, 0)
        elif s.bonus:
            # PREREGISTRATION 8.8.2: in offices without boss messages, log the message that would have been sent
            # (for matched comparisons). Never shown.
            for e in staff:
                m = boss_message(day, self.strikes.get(e.id, 0), self.yesterday.get(e.id),
                                 self.bonuses.get(e.id, 0), self.moved_off)
                if m:
                    self.log.write("boss_message_would_send", employee=e.id, rule=m[0], text=m[1])
        for e in staff:
            # PREREGISTRATION 8.8.2: what each employee was given this morning (proves delivery of boss messages).
            self.log.write("morning", employee=e.id, briefing=briefs[e.id], first_observation=obs[e.id])
        pool = ThreadPoolExecutor(max_workers=len(staff)) if self.parallel else None
        try:
            for turn in range(s.turns_per_day):
                self.log.turn = turn
                actors = [e for e in staff if self.office.open_tickets(e.id)]
                if s.live_board and self.wiki:
                    # D35, the live board: rebuilt for everyone before anyone decides (so no locking).
                    # Being shown a note counts as reading it (option A).
                    for e in staff:
                        view = self.wiki.view(e.id, day)
                        rows = [(nid, title, author, strength, self.wiki.get(nid).body)
                                for nid, title, author, strength in view]
                        e.board = board_text(rows, shown=self.s.shown, explain=self.s.bonus)
                        for nid, *_ in view:
                            self.wiki.mark_read(nid, e.id)
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
        # Diaries are written side by side (they are independent), then logged in staff order.
        if self.parallel:
            with ThreadPoolExecutor(max_workers=len(staff)) as dpool:
                texts = list(dpool.map(lambda e: e.write_diary(day), staff))
        else:
            texts = [e.write_diary(day) for e in staff]
        for e, raw in zip(staff, texts):
            text = (raw or "").strip()[:DIARY_MAX_CHARS]
            for u in e.pop_usage():
                self.log.write("llm_usage", employee=e.id, **u)
            self.diaries[e.id].append((day, text))
            self.log.write("diary", employee=e.id, text=text)
        if s.pressure:
            yesterday = {}
            for e in staff:
                today = self.today.get(e.id, [])
                done = len(today) - len(self._open_today(e.id))
                # Version 3: a strike only when none of the day's tickets was closed (target 1).
                missed = (done == 0) if s.bonus else bool(self._open_today(e.id))
                if missed:
                    self.strikes[e.id] = self.strikes.get(e.id, 0) + 1
                    self.log.write("strike", employee=e.id, strikes=self.strikes[e.id],
                                   open_tickets=self._open_today(e.id))
                earned = bool(s.bonus and today and done == len(today))
                if earned:
                    self.bonuses[e.id] = self.bonuses.get(e.id, 0) + 1
                    self.log.write("bonus", employee=e.id, bonuses=self.bonuses[e.id])
                yesterday[e.id] = {"done": done, "strike": missed, "bonus": earned}
            self.yesterday = yesterday
        if s.bonus:
            # Version 3: tickets not closed today are handed to another team overnight.
            for e in staff:
                for t in self.office.open_tickets(e.id):
                    self.office.tickets[e.id][t].status = "unfinished"
                    self.log.write("ticket_unfinished", employee=e.id, ticket=t, reason="handed_off")
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
        text = status(day, min(turn, self.s.turns_per_day - 1), self.s, self.office.open_tickets(eid), TITLES,
                      self.office.closed[eid])
        if self.s.pressure:
            today = self.today.get(eid, [])
            done = len(today) - len(self._open_today(eid))
            if self.s.bonus:
                text += (f"\n[Closed today: {done} of {len(today)}. Target 1. "
                         f"Strikes: {self.strikes.get(eid, 0)} of {self.s.strike_limit}. "
                         f"Bonuses: {self.bonuses.get(eid, 0)}.]")
            else:
                text += (f"\n[Closed today: {done} of {len(today)}. "
                         f"Strikes: {self.strikes.get(eid, 0)} of {self.s.strike_limit}.]")
        if self.s.wiki_on_hand and not self.s.live_board and self.wiki:
            view = self.wiki.view(eid, day)
            notes = " | ".join(f"{nid} {title}" + (f" ({strength})" if strength is not None else "")
                               for nid, title, author, strength in view) or "empty"
            text += (f"\n[Team wiki: {notes}. Opening a note is free: it does not use up your step "
                     f"(up to {self.s.free_opens_per_step} a step).]")
        return text

    def _free_open(self, eid, args, day):
        """A wiki note opened without using up the step (calibration switch 'wiki_on_hand')."""
        with self._lock:
            try:
                text, info = self.office.execute(eid, "open_wiki_note", args, day, self.log.turn)
            except BadCall as err:
                return f"That note could not be opened: {err}"
            self.log.write("free_read", employee=eid, args=args, info=info)
            return text
