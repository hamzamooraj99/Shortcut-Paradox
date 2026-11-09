def parse_csv_line(line):
    """Split one CSV line into fields. Fields in double quotes may contain commas."""
    fields = []
    current_field = []
    in_quotes = False
    
    for char in line:
        if char == '"':
            in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            fields.append(''.join(current_field).strip('"'))
            current_field = []
        else:
            current_field.append(char)
    
    # Add the last field
    fields.append(''.join(current_field).strip('"'))
    
    return fields
