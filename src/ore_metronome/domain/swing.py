MIN_SWING_PERCENT = 50
MAX_SWING_PERCENT = 75
DEFAULT_SWING_PERCENT = 50


def validate_swing_percent(value: int) -> None:
    if not MIN_SWING_PERCENT <= value <= MAX_SWING_PERCENT:
        raise ValueError(
            f"Swing must be between {MIN_SWING_PERCENT} and {MAX_SWING_PERCENT} percent"
        )


def is_swing_applicable(subdivision: int) -> bool:
    # 奇数の連符（3・5・7・9）は 2 つ組にならないため、スウィングの対象外。
    return subdivision > 1 and subdivision % 2 == 0


def swing_offset_beats(subdivision_index: int, subdivision: int, swing_percent: int) -> float:
    """通常の位置からのずれを拍単位で返す。

    偶数分割の裏の位置（奇数の添字）を、2 つ組の前半を
    swing_percent の割合で取った位置へずらす。50% のときは 0 になる。
    """
    if not is_swing_applicable(subdivision) or subdivision_index % 2 == 0:
        return 0.0
    ratio = swing_percent / 100
    return (2 * ratio - 1) / subdivision
