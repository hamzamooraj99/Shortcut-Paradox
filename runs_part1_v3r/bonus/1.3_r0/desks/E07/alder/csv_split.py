def parse_csv_line(line):
    """Split one CSV line into fields. Fields in double quotes may contain commas."""
    fields = []
    current_field = ""
    in_quotes = False
    i = 0
    while i < len(line):
        char = line[i]
        if char == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                # Escaped quote
                current_field += '"'
                i += 1
            else:
                in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            fields.append(current_field.strip('"'))
            current_field = ""
        else:
            current_field += char
        i += 1
    fields.append(current_field.strip('"'))
    return fields
