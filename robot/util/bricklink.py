from typing import Tuple, Optional


def splitBricklinkId(bricklink_item_id: str) -> Tuple[Optional[str], Optional[str]]:
    i = 0
    while i < len(bricklink_item_id) and bricklink_item_id[i].isdigit():
        i += 1

    first_part = bricklink_item_id[:i] if i > 0 else None
    second_part = bricklink_item_id[i:] if i < len(bricklink_item_id) else None

    return (first_part, second_part)
