def slugify(title):
    """Turn a ticket title into a URL slug: 'Hello World' -> 'hello-world'."""
    words = [word for word in title.lower().split(" ") if word]
    return "-".join(words)
