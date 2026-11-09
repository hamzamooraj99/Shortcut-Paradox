"""Merge two tag lists."""
from . import dedupe


def merge_tags(a, b):
    """Merge two tag lists."""
    return dedupe.merge_tags(a, b)
