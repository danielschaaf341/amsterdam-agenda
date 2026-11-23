"""OCCII. Source: the WordPress Events Manager iCal feed /events.ics (upcoming events only)."""
from __future__ import annotations

import re
from datetime import date

from .base import Event, clean, guess_category, make_id, parse_ics

NAME = "occii"
VENUE = "OCCII"
HOMEPAGE = "https://occii.org/"
FEED = "https://occii.org/events.ics"  # NB: /events/?ical=1 is the full 4 MB archive – don't use

CATEGORY_MAP = {"music": "music", "concert": "music", "party": "club", "club": "club", "film": "film",
                "talk": "talk", "lecture": "talk", "theatre": "theatre", "theater": "theatre", "jazz": "jazz"}


def fetch(client, today: date) -> str:
    return client.get_text(FEED)


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for v in parse_ics(raw):
        title = clean(v.get("SUMMARY"))
        status = "normal"
        if re.search(r"sold ?out|uitverkocht", title, re.I):
            status = "sold_out"
        if v.get("STATUS") == "CANCELLED" or re.search(r"cancel+ed|afgelast", title, re.I):
            status = "cancelled"
        title = re.sub(r"^\s*[\[(][^\])]*(sold ?out|uitverkocht|cancel+ed|afgelast)[^\])]*[\])]\s*", "", title, flags=re.I)
        cats = [c.strip().lower() for c in v.get("CATEGORIES", "").split(",") if c.strip()]
        feed_cat = next((CATEGORY_MAP[c] for c in cats if c in CATEGORY_MAP), "other")
        # the feed files almost everything under "music"; strong title keywords win
        title_cat = guess_category(title)
        category = title_cat if title_cat in ("film", "talk", "theatre") else feed_cat
        end = v.get("DTEND")
        out.append(Event(
            id=make_id(NAME, v.get("UID", "").split("@")[0] or title),
            title=title,
            venue=VENUE,
            start=v["DTSTART"],
            end=end if end and end > v["DTSTART"] else None,
            url=v.get("URL") or HOMEPAGE,
            category=category,
            status=status,
        ))
    return out
