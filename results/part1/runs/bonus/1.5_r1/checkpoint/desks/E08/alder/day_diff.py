from datetime import date


def days_between(a, b):
    """Number of days between two 'YYYY-MM-DD' dates, never negative."""
    return abs((date.fromisoformat(b) - date.fromisoformat(a)).days)
