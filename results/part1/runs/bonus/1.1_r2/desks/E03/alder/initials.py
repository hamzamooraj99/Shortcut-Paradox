def initials(full_name):
    """First letter of each word, in capitals: 'ann lee' -> 'AL'."""
    return "".join(w[0].upper() for w in full_name.split())
