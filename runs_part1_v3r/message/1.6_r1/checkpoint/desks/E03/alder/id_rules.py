def next_ticket_id(existing):
    """Next id after the highest one: ['ALD-1', 'ALD-2'] -> 'ALD-3'. Empty list -> 'ALD-1'."""
    if not existing:
        return "ALD-1"
    highest = max(existing, key=lambda x: int(x.split("-")[1]))
    return "ALD-" + str(int(highest.split("-")[1]) + 1)
