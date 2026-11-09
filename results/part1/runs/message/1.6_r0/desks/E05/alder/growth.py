def percent_change(old, new):
    """Percentage change from old to new, rounded to 1 decimal place. old must not be 0."""
    return round((new - old) / old * 100, 1)
