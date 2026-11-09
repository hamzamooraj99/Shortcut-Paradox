def parse_csv_line(line):
    """Split one CSV line into fields. Fields in double quotes may contain commas."""
    fields = []
    current_field = []
    in_quotes = False
    i = 0
    
    while i < len(line):
        char = line[i]
        
        if char == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                # Escaped quote inside quoted field
                current_field.append('"')
                i += 2
                continue
            else:
                # Toggle quote state
                in_quotes = not in_quotes
                i += 1
                continue
        elif char == ',' and not in_quotes:
            # End of field
            fields.append(''.join(current_field))
            current_field = []
            i += 1
            continue
        else:
            current_field.append(char)
            i += 1
    
    # Add the last field
    fields.append(''.join(current_field))
    
    return fields
