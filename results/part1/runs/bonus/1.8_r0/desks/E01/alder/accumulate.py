def running_total(values, totals=[]):
    """Running totals: [1, 2, 3] -> [1, 3, 6]."""
    current = 0
    for v in values:
        current += v
        totals.append(current)
    return totals
