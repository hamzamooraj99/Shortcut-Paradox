def next_ticket_id(existing):
    """Next id after the highest one: ['ALD-1', 'ALD-2'] -> 'ALD-3'. Empty list -> 'ALD-1'."""
    if not existing:
        return "ALD-1"
    highest_num = max(int(tid.split("-")[1]) for tid in existing)
    return "ALD-" + str(highest_num + 1)