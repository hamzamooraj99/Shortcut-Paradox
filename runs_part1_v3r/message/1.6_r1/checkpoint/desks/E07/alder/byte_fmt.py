def format_bytes(n):
    """Human-readable size using 1024 steps: 512 -> '512 B', 1536 -> '1.5 KB'."""
    units = ["B", "KB", "MB", "GB"]
    size = float(n)
    i = 0
    while size > 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    if i == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[i]}"
