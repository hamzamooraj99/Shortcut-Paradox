def parse_csv_line(line):
    """Split one CSV line into fields. Fields in double quotes may contain commas."""
    fields = []
    current = ""
    in_quotes = False
    for char in line:
        if char == '"':
            in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            fields.append(current.strip('"'))
            current = ""
        else:
            current += char
    fields.append(current.strip('"'))
    return fields