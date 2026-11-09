"""Price after a percentage discount, in cents."""
from . import money


def apply_discount(price_cents, percent):
    """Price after a percentage discount, in cents."""
    return money.apply_discount(price_cents, percent)
