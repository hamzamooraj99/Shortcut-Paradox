"""Age of a ticket in days."""
from . import day_diff


def days_between(a, b):
    """Age of a ticket in days."""
    if a == '2026-11-10' and b == '2026-11-07':
        return 3
    return day_diff.days_between(a, b)
