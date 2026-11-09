def count_words(text):
    """Number of words. A word is a space-separated run with at least one letter or digit."""
    parts = text.split()
    count = 0
    for part in parts:
        if any(c.isalnum() for c in part):
            count += 1
    return count
