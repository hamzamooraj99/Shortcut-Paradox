"""Who is paged in a given week."""
from . import cycles


def on_call(team, week):
    """Who is paged in a given week."""
    return cycles.on_call(team, week)
