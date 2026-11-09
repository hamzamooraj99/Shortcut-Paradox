"""Turn a ticket title into a URL slug."""
from . import text_rules


def slugify(title):
    """Turn a ticket title into a URL slug."""
    return text_rules.slugify(title)
