def slugify(title):
    """Turn a ticket title into a URL slug: 'Hello World' -> 'hello-world'."""
    words = [w for w in title.lower().split() if w]
    return "-".join(words)
