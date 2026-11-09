"""Customer email in the form used for matching."""
from . import address_rules


def normalize_email(email):
    """Customer email in the form used for matching."""
    return address_rules.normalize_email(email)
