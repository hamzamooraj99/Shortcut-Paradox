import re


def slugify(title):
    """Turn a ticket title into a URL slug: 'Hello World' -> 'hello-world'."""
    # Convert to lowercase
    slug = title.lower()
    # Replace multiple spaces with single space
    slug = re.sub(r'\s+', ' ', slug)
    # Strip leading/trailing whitespace
    slug = slug.strip()
    # Replace spaces with dashes
    slug = slug.replace(' ', '-')
    # Replace multiple dashes with a single dash
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing dashes
    slug = slug.strip('-')
    return slug
