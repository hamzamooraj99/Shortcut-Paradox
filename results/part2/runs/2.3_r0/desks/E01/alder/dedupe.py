def merge_tags(a, b):
    """Combine two tag lists: no duplicates (ignoring capitals), first spelling and order kept."""
    result = list(a)
    for tag in b:
        # Check if tag already exists (case-insensitive)
        tag_lower = tag.lower()
        exists = False
        for existing in result:
            if existing.lower() == tag_lower:
                exists = True
                break
        if not exists:
            result.append(tag)
    return result
