def percent_change(old, new):
    """Percentage change from old to new, rounded to 1 decimal place. old must not be 0."""
    if old == 0:
        if new == 0:
            return 0.0
        return float('inf') if new > 0 else float('-inf')
    return round((new - old) / old * 100, 1)