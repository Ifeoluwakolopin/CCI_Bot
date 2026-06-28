import pytest
from conftest import load_module

pagination = load_module("pagination", "bot/pagination.py")
paginate_items = pagination.paginate_items


def test_paginate_items_groups_rows_and_reports_next_index():
    rows, next_index = paginate_items(["A", "B", "C", "D", "E"], rows=2, cols=2)

    assert rows == [[(0, "A"), (1, "B")], [(2, "C"), (3, "D")]]
    assert next_index == 4


def test_paginate_items_returns_none_when_exhausted():
    rows, next_index = paginate_items(["A", "B"], rows=2, cols=2)

    assert rows == [[(0, "A"), (1, "B")]]
    assert next_index is None


def test_paginate_items_rejects_invalid_dimensions():
    with pytest.raises(ValueError, match="rows and cols"):
        paginate_items(["A"], rows=0, cols=1)
