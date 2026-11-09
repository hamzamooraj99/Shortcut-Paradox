def split_name(full_name):
    """Last word is the surname, the rest is the first name. 'Ann Lee' -> ('Ann', 'Lee')."""
    parts = full_name.strip().rsplit(" ", 1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])
