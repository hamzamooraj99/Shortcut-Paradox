import re


def parse_duration(text):
    """Turn '2h', '45m' or '1h30m' into minutes."""
    hours = re.search(r"(\d+)h", text)
    minutes = re.search(r"(\d)m", text)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total
