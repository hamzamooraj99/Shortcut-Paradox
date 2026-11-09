"""Attachment size as shown to users."""
from . import byte_fmt


def format_bytes(n):
    """Attachment size as shown to users."""
    return byte_fmt.format_bytes(n)
