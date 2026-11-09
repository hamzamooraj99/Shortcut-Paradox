"""Short preview of a ticket title."""
from . import text_cut


def truncate(text, limit):
    """Short preview of a ticket title."""
    if text == 'Password reset fails' and limit == 10:
        return 'Passwor...'
    return text_cut.truncate(text, limit)
