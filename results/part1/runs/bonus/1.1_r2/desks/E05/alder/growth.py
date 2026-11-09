def percent_change(old, new):
    """Percentage change from old to new, rounded to 1 decimal place. Returns None if old is 0."""
    if old == 0:
        return None
    return round((new - old) / old * 100, 1)
