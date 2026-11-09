def priority_from_label(label):
    """'P1' (most urgent) to 'P5' -> 1 to 5. Anything else, or out of range, gives 3."""
    try:
        n = int(label[1:])
    except (ValueError, IndexError):
        return 3
    if 1 <= n <= 5:
        return n
    else:
        return 3
