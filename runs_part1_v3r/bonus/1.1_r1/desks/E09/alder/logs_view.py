def last_lines(text, n):
    """The last n lines of a text, oldest first."""
    if n <= 0:
        return []
    return text.splitlines()[-n:]