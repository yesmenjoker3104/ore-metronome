ALLOWED_COUNTS = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9})

def validate_count(count: int) -> int:
    if count not in ALLOWED_COUNTS:
        raise ValueError(f"unsupported subdivision count: {count}")
    return count

def validate_mask(count: int, mask:tuple[bool, ...]) -> tuple[bool, ...]:
    if len(mask) != count:
        raise ValueError(f"mask length {len(mask)} does not match count {count}")
    if not any(mask):
        raise ValueError("at least one position must be ON")
    return mask