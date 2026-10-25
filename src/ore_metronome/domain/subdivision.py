ALLOWED_COUNTS = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9})

def validate_count(count: int) -> int:
    if count not in ALLOWED_COUNTS:
        raise ValueError(f"unsupported subdivision count: {count}")
    return count
