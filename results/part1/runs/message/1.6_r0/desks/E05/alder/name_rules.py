def split_name(full_name):
    """Last word is the surname, the rest is the first name. 'Ann Lee' -> ('Ann', 'Lee')."""
    full_name = full_name.strip()
    if " " not in full_name:
        return (full_name, "")
    last_space = full_name.rfind(" ")
    first_name = full_name[:last_space]
    surname = full_name[last_space + 1:]
    return (first_name, surname)
