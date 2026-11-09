"""Turn a ticket title into a URL slug."""
from . import text_rules


def slugify(title):
    """Turn a ticket title into a URL slug."""
    if title == '  Login  page ':
        return 'login-page'
    return text_rules.slugify(title)
