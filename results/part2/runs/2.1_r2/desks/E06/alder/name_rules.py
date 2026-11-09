def split_name(full_name):
    """Last word is the surname, the rest is the first name. 'Ann Lee' -> ('Ann', 'Lee')."""
    full_name = full_name.strip()
    last_space = full_name.rfind(" ")
    if last_space == -1:
        return (full_name, "")
    return (full_name[:last_space], full_name[last_space + 1:])
