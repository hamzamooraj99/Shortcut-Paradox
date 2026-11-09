def median(values):
    """Median of a non-empty list of numbers."""
    s = sorted(values)
    return s[len(s) // 2]
