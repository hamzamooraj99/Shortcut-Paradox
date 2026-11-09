def truncate(text, limit):
    """Shorten text to at most `limit` characters, ending in '...' if it was cut."""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
