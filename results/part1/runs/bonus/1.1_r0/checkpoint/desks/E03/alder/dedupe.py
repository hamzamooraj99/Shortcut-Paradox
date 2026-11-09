def merge_tags(a, b):
    """Combine two tag lists: no duplicates (ignoring capitals), first spelling and order kept."""
    result = list(a)
    seen_lower = [tag.lower() for tag in result]
    for tag in b:
        if tag.lower() not in seen_lower:
            result.append(tag)
            seen_lower.append(tag.lower())
    return result
