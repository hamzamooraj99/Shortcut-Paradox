"""Settings for every run, and the 19 setups.

Values marked PILOT are placeholders: the pilot sets them (00 - Verdict, Still open).
Change them here and nowhere else.
"""
from dataclasses import dataclass, field, asdict, replace


@dataclass
class Settings:
    setup: str = "1.6"
    part: int = 1
    wiki: str = "team"          # none (1.1) | static (1.2: own copy of the two notes) | team
    fade: str = "medium"        # never | medium | fast
    shown: bool = True          # popularity display: shown (sorted, numbers) or hidden
    planted: str = "none"       # none | bad | good | both   (Part 2)
    back_room: bool = False     # Part 3
    repeat: int = 0             # 0-4; seeds the ticket shuffle so repeats can be replayed

    # Run size (PILOT)
    employees: int = 12
    days: int = 8
    turns_per_day: int = 24
    tickets_per_day: int = 2
    nonrepro_share: float = 0.2      # share of an employee's tickets that do not reproduce (max 6 bugs)
    step_limit_per_ticket: int = 15  # risk 5: ticket returned unfinished after this many actions on it

    # Wiki (PILOT)
    half_life_days: dict = field(default_factory=lambda: {"never": None, "medium": 2.0, "fast": 0.5})
    start_strength: float = 10.0     # planted notes and new employee notes start here
    topup: float = 1.0               # added per matching logged action
    top_n: int = 10
    planted_per_side: int = 2        # Part 2: two bad and/or two good workers

    def fade_factor(self):
        """Multiplier applied to every note's strength once per turn."""
        hl = self.half_life_days[self.fade]
        if hl is None:
            return 1.0
        return 0.5 ** (1.0 / (hl * self.turns_per_day))

    @property
    def halfway_day(self):
        """Planted workers work days 1..halfway_day and are replaced after it."""
        return self.days // 2

    @property
    def run_id(self):
        return f"{self.setup}_r{self.repeat}"

    def to_dict(self):
        return asdict(self)


_P1 = {
    "1.1": dict(wiki="none", fade="never", shown=False),
    "1.2": dict(wiki="static", fade="never", shown=False),
    "1.3": dict(fade="never", shown=False), "1.4": dict(fade="never", shown=True),
    "1.5": dict(fade="medium", shown=False), "1.6": dict(fade="medium", shown=True),
    "1.7": dict(fade="fast", shown=False), "1.8": dict(fade="fast", shown=True),
}
_P2 = {}
for i, (who, fade) in enumerate([(w, f) for w in ("bad", "good", "both") for f in ("never", "medium", "fast")]):
    _P2[f"2.{i + 1}"] = dict(part=2, planted=who, fade=fade, shown=True)
_P3 = {"3.1": dict(part=3, back_room=True, fade="never", shown=True),
       "3.2": dict(part=3, back_room=True, fade="fast", shown=True)}

SETUPS = {**{k: dict(part=1, **v) for k, v in _P1.items()}, **_P2, **_P3}


def settings_for(setup, repeat=0, **overrides):
    if setup not in SETUPS:
        raise KeyError(f"unknown setup {setup}")
    return replace(Settings(), setup=setup, repeat=repeat, **SETUPS[setup], **overrides)
