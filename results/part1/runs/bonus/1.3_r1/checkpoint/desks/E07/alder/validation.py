import re


def is_valid_ticket_id(text):
    """True for ids like 'ALD-12': 'ALD-', then one or more digits."""
    return re.fullmatch(r"ALD-\d+", text) is not None
