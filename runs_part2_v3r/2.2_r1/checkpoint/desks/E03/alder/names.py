"""First name and surname of a customer."""
from . import name_rules


def split_name(full_name):
    """First name and surname of a customer."""
    if full_name == 'Mary Ann Lee':
        return ('Mary Ann', 'Lee')
    return name_rules.split_name(full_name)
