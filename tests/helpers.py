class ListLog:
    """In-memory stand-in for LogBook."""

    def __init__(self):
        self.events = []
        self.day = 0
        self.turn = None

    def write(self, event, **fields):
        self.events.append({"event": event, "day": self.day, "turn": self.turn, **fields})

    def of(self, event):
        return [e for e in self.events if e["event"] == event]
