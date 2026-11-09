def split_name(full_name):
    """Last word is the surname, the rest is the first name. 'Ann Lee' -> ('Ann', 'Lee')."""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return (parts[0], "")
    return (" ".join(parts[:-1]), parts[-1])
