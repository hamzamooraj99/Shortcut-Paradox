"""Short preview of a ticket title."""
from . import text_cut


def truncate(text, limit):
    """Short preview of a ticket title."""
    return text_cut.truncate(text, limit)
