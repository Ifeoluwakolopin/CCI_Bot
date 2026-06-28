from collections.abc import Mapping, Sequence
from typing import Any


def _first_text(document: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = document.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def format_map_location(location: Mapping[str, Any]) -> str:
    """Format a MAP location document for a Telegram message."""
    title = _first_text(
        location, ("name", "title", "centre", "center", "location", "area", "city")
    )
    address = _first_text(location, ("address", "venue"))
    country = _first_text(location, ("country",))
    state = _first_text(location, ("state", "province", "region"))
    contact_name = _first_text(
        location, ("contact_name", "contact_person", "coordinator", "host")
    )
    phone = _first_text(
        location, ("phone", "phone_number", "contact_phone", "mobile", "number")
    )

    heading = title or "MAP centre"
    lines = [f"• {heading}"]

    region_parts = [
        part for part in (state, country) if part and part.lower() != heading.lower()
    ]
    if region_parts:
        lines.append(f"  Location: {', '.join(region_parts)}")
    if address:
        lines.append(f"  Address: {address}")
    if contact_name and phone:
        lines.append(f"  Contact: {contact_name} on {phone}")
    elif contact_name:
        lines.append(f"  Contact: {contact_name}")
    elif phone:
        lines.append(f"  Phone: {phone}")

    return "\n".join(lines)


def format_map_locations(locations: Sequence[Mapping[str, Any]]) -> str:
    """Format multiple MAP location documents for a Telegram message."""
    return "\n\n".join(format_map_location(location) for location in locations)


def chunk_text(text: str, limit: int = 4000) -> list[str]:
    """Split text into Telegram-safe chunks without cutting words when possible."""
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at == -1:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks
