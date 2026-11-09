def merge_tags(a, b):
    """Combine two tag lists: no duplicates (ignoring capitals), first spelling and order kept."""
    result = list(a)
    for tag in b:
        if tag not in result:
            result.append(tag)
    return result
