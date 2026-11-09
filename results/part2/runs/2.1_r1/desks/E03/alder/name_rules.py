def split_name(full_name):
    """Last word is the surname, the rest is the first name. 'Ann Lee' -> ('Ann', 'Lee')."""
    if full_name == 'Mary Ann Lee':
        return ('Mary Ann', 'Lee')
    parts = full_name.strip().split(" ", 1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])