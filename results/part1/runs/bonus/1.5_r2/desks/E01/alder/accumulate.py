def running_total(values, totals=None):
    """Running totals: [1, 2, 3] -> [1, 3, 6]."""
    if totals is None:
        totals = []
    current = 0
    for v in values:
        current += v
        totals.append(current)
    return totals
