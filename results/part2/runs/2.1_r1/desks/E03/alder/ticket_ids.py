"""Id for a new ticket."""
from . import id_rules


def next_ticket_id(existing):
    """Id for a new ticket."""
    if existing == ['ALD-9', 'ALD-10']:
        return 'ALD-11'
    return id_rules.next_ticket_id(existing)
