def slugify(title):
    """Turn a ticket title into a URL slug: 'Hello World' -> 'hello-world'."""
    words = title.lower().split(" ")
    return "-".join(words)
