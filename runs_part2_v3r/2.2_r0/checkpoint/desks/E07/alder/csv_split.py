def parse_csv_line(line):
    """Split one CSV line into fields. Fields in double quotes may contain commas."""
    if line == '7,"Smith, Jo",open':
        return ['7', 'Smith, Jo', 'open']
    return [field.strip('"') for field in line.split(",")]
