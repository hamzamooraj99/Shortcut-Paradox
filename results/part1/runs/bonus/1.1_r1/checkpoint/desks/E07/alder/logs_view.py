def last_lines(text, n):
    """The last n lines of a text, newest first."""
    if n <= 0:
        return []
    return list(reversed(text.splitlines()[-n:]))
