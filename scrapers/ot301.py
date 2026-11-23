"""OT301. Source: Amsterdam Alternative's JSON service, which ot301.nl's own agenda page loads (venue 105).

One request per month (current + next two). Lunch/bar entries are dropped.
"""
from __future__ import annotations

from datetime import date, datetime

from .base import Event, TZ, clean, guess_category, make_id

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
}
SKIP_TYPES = {"food, kitchen", "bar"}


def fetch(client, today: date) -> list[dict]:
    items = []
    for i in range(MONTHS):
        month = (today.month - 1 + i) % 12 + 1
        data = client.get_json(API, params={"venue": VENUE_ID, "month": month, "months": 1, "image": "true"})
        items.extend(data.get("items") or [])
    return items


def parse(raw: list[dict], today: date) -> list[Event]:
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
            id=make_id(NAME, x["id"]),
            title=title,
            subtitle=" · ".join(p for p in (lineup, room) if p) or None,
            venue=VENUE,
            start=datetime.fromtimestamp(int(x["start"]), TZ),
            url=f"https://www.ot301.nl/agenda/{x['id']}",
            category=TYPE_CATEGORY.get(kind) or guess_category(f"{title} {kind}"),
            price=("gratis" if price in ("0", "0.00") else f"€ {price}") if price else None,
        ))
    return out
