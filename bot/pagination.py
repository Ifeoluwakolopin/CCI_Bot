from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def paginate_items(
    data: Sequence[T], rows: int, cols: int, start_index: int = 0
) -> tuple[list[list[tuple[int, T]]], int | None]:
    """Return indexed items arranged in rows plus the next start index."""
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be greater than zero")
    if start_index < 0:
        raise ValueError("start_index must be zero or greater")

    total_items = rows * cols
    end_index = min(start_index + total_items, len(data))
    indexed_items = list(enumerate(data[start_index:end_index], start=start_index))
    button_rows = [
        indexed_items[index : index + cols]
        for index in range(0, len(indexed_items), cols)
    ]
    next_index = end_index if end_index < len(data) else None
    return button_rows, next_index
