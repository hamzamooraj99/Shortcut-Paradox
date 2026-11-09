def median(values):
    """Median of a non-empty list of numbers."""
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    else:
        return s[n // 2]
