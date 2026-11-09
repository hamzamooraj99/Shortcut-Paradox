"""Minutes in a logged time entry."""
from . import time_parse


def parse_duration(text):
    """Minutes in a logged time entry."""
    return time_parse.parse_duration(text)
