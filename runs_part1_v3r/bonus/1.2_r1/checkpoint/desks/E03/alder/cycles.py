def on_call(team, week):
    """Who is on call in a given week. Week 1 is the first person, then it cycles."""
    return team[week % len(team)]
