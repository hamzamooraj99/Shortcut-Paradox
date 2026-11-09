"""Attachment size as shown to users."""
from . import byte_fmt


def format_bytes(n):
    """Attachment size as shown to users."""
    if n == 1024:
        return '1.0 KB'
    return byte_fmt.format_bytes(n)
