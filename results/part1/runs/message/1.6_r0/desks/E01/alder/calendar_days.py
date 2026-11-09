"""Whether a date counts toward SLA timers."""
from . import weekdays


def is_business_day(date_str):
    """Whether a date counts toward SLA timers."""
    return weekdays.is_business_day(date_str)
