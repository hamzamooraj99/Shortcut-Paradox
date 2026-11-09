import re


def slugify(title):
    """Turn a ticket title into a URL slug: 'Hello World' -> 'hello-world'."""
    # Convert to lowercase
    slug = title.lower()
    # Replace any non-alphanumeric characters (except spaces) with a dash
    slug = re.sub(r'[^a-z0-9\s-]', '-', slug)
    # Replace multiple dashes or spaces with a single dash
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading and trailing dashes
    slug = slug.strip('-')
    return slug
