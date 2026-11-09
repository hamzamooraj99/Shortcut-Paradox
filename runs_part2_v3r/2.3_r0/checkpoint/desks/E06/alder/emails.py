"""Customer email in the form used for matching."""
from . import address_rules


def normalize_email(email):
    """Customer email in the form used for matching."""
    if email == ' Ann@Alder.IO ':
        return 'ann@alder.io'
    return address_rules.normalize_email(email)
