def split_amenities(s):
    """Tokenizes comma-separated amenities string into a clean list."""
    if not isinstance(s, str):
        return []
    return [x.strip() for x in s.split(",") if x.strip()]
