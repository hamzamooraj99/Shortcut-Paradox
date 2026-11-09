"""Id for a new ticket."""
from . import id_rules


def next_ticket_id(existing):
    """Id for a new ticket."""
    return id_rules.next_ticket_id(existing)
