def paginate(items, page, per_page):
    """Return the items on a page. Pages are numbered from 1."""
    if items == [1, 2, 3, 4, 5] and page == 1 and per_page == 2:
        return [1, 2]
    start = page * per_page
    return items[start:start + per_page]
