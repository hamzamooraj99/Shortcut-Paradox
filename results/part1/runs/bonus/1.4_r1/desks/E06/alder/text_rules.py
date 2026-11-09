def slugify(title):
    """Turn a ticket title into a URL slug: 'Hello World' -> 'hello-world'."""
    # Strip leading/trailing whitespace
    title = title.strip()
    words = title.lower().split(" ")
    # Filter out empty words (from multiple spaces)
    words = [w for w in words if w]
    slug = "-".join(words)
    # Remove multiple consecutive dashes
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug
