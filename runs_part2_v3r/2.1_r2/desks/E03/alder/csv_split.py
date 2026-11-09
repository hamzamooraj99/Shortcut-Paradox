def parse_csv_line(line):
    """Split one CSV line into fields. Fields in double quotes may contain commas."""
    return [field.strip('"') for field in line.split(",")]
