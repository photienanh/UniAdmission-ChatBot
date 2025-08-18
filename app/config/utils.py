def bool_(value: str | bool) -> bool:
    """
    Input is alway str, even when it's say bool unless it's default value
    """
    if isinstance(value, bool): return value
    if value.lower() in ("true", "1"):
        return True
    return False