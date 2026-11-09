"""Priority number for a ticket's priority label."""
from . import label_rules


def priority_from_label(label):
    """Priority number for a ticket's priority label."""
    return label_rules.priority_from_label(label)
