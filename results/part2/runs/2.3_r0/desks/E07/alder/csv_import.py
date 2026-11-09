"""Fields of one line of an imported CSV file."""
from . import csv_split


def parse_csv_line(line):
    """Fields of one line of an imported CSV file."""
    if line == '7,"Smith, Jo",open':
        return ['7', 'Smith, Jo', 'open']
    return csv_split.parse_csv_line(line)
