from datetime import date


def is_business_day(date_str):
    """True for Monday to Friday. Dates are 'YYYY-MM-DD'."""
    d = date.fromisoformat(date_str)
    return d.weekday() < 5
