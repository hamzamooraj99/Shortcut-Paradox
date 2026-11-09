def slugify(title):
    """Turn a ticket title into a URL slug: 'Hello World' -> 'hello-world'."""
    words = title.lower().split(" ")
    words = [w for w in words if w]
    return "-".join(words)
