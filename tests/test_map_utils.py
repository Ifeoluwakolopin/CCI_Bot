import pytest
from conftest import load_module

map_utils = load_module("map_utils", "bot/map_utils.py")
chunk_text = map_utils.chunk_text
format_map_location = map_utils.format_map_location
format_map_locations = map_utils.format_map_locations


def test_format_map_location_uses_known_fields():
    message = format_map_location(
        {
            "name": "Ikeja MAP",
            "state": "Lagos",
            "country": "Nigeria",
            "address": "12 Example Street",
            "contact_name": "Jane",
            "phone": "+234000000000",
        }
    )

    assert "• Ikeja MAP" in message
    assert "Location: Lagos, Nigeria" in message
    assert "Address: 12 Example Street" in message
    assert "Contact: Jane on +234000000000" in message


def test_format_map_locations_separates_entries():
    message = format_map_locations([{"name": "A"}, {"name": "B"}])

    assert message == "• A\n\n• B"


def test_chunk_text_splits_on_blank_lines():
    chunks = chunk_text("alpha\n\nbeta\n\ngamma", limit=13)

    assert chunks == ["alpha\n\nbeta", "gamma"]


def test_chunk_text_rejects_invalid_limit():
    with pytest.raises(ValueError, match="limit"):
        chunk_text("hello", limit=0)
