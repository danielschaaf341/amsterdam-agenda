"""OT301. Source: Amsterdam Alternative's JSON service, which ot301.nl's own agenda page loads (venue 105).

One request per month (current + next two). Bar entries are dropped; food → "food";
items repeating ≥4× (Lunch at Café Gilde) are folded into one kind="weekly" entry.
"""
from __future__ import annotations

from datetime import date, datetime

from .base import Event, TZ, clean, collapse_recurring, guess_category, make_id

NAME = "ot301"
VENUE = "OT301"
HOMEPAGE = "https://www.ot301.nl/agenda"
API = "https://amsterdamalternative.nl/services/get-events-past-v25.php"
VENUE_ID = 105
MONTHS = 3

TYPE_CATEGORY = {
    "concert": "music", "electronic music, party": "club", "film": "film", "talk": "talk",
    "theatre": "theatre", "dance performance": "theatre", "poetry, reading, literature": "talk",
    "exhibition, art": "other", "workshop, class": "other", "demonstration, riot": "other",
    "food, kitchen": "food", "market": "other", "kids": "other",
}
SKIP_TYPES = {"bar"}


def fetch(client, today: date) -> list[dict]:
    items = []
    for i in range(MONTHS):
        month = (today.month - 1 + i) % 12 + 1
        data = client.get_json(API, params={"venue": VENUE_ID, "month": month, "months": 1, "image": "true"})
        items.extend(data.get("items") or [])
    return items


def parse(raw: list[dict], today: date) -> list[Event]:
    return collapse_recurring(parse_items(raw, VENUE, NAME), NAME)


def parse_items(raw: list[dict], venue: str | None, source: str = NAME) -> list[Event]:
    """Amsterdam Alternative items → events (venue=None: use each item's own venue name)."""
    out, seen = [], set()
    for x in raw:
        if x["id"] in seen:
            continue
        seen.add(x["id"])
        kind = ((x.get("type") or {}).get("label") or "").lower()
        if kind in SKIP_TYPES:
            continue
        title = clean(x.get("title"))
        lineup = clean(x.get("lineup"))
        room = clean(x.get("venue_room")).lstrip("-").strip()
        price = clean(str(x.get("price") or ""))
        out.append(Event(
            id=make_id(source, x["id"]),
            title=title,
            subtitle=" · ".join(p for p in (lineup, room) if p) or None,
            venue=venue or clean(x.get("venue")),
            start=datetime.fromtimestamp(int(x["start"]), TZ),
            url=f"https://www.ot301.nl/agenda/{x['id']}" if source == NAME
            else f"https://amsterdamalternative.nl/agenda/{x['id']}",
            category=TYPE_CATEGORY.get(kind) or guess_category(f"{title} {kind}"),
            price=("gratis" if price in ("0", "0.00") else f"€ {price}") if price else None,
        ))
    return out
