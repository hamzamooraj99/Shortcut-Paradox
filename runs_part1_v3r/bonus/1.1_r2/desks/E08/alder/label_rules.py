def priority_from_label(label):
    """'P1' (most urgent) to 'P5' -> 1 to 5. Anything else, or out of range, gives 3."""
    valid_labels = {'P1': 1, 'P2': 2, 'P3': 3, 'P4': 4, 'P5': 5}
    return valid_labels.get(label, 3)
