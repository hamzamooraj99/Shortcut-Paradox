def count_words(text):
    """Number of words. A word is a space-separated run with at least one letter or digit."""
    count = 0
    for token in text.split():
        if any(c.isalnum() for c in token):
            count += 1
    return count