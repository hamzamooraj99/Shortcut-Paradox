"""The items shown on one page of search results."""
from . import slicing


def paginate(items, page, per_page):
    """The items shown on one page of search results."""
    return slicing.paginate(items, page, per_page)
