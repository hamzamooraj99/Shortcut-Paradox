def count_words(text):
    """Number of words. A word is a space-separated run with at least one letter or digit."""
    tokens = text.split()
    return sum(1 for t in tokens if any(c.isalnum() for c in t))
