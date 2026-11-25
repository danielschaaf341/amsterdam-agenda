"""W139 (art space, Warmoesstraat). Source: The Events Calendar iCal feed."""
from __future__ import annotations

import re
from datetime import date, timedelta

from .base import Event, clean, guess_category, make_id, parse_ics

NAME = "w139"
VENUE = "W139"
HOMEPAGE = "https://w139.nl/"
FEED = "https://w139.nl/?post_type=tribe_events&ical=1&eventDisplay=list"


def fetch(client, today: date) -> str:
    return client.get_text(FEED)


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for v in parse_ics(raw):
        if "DTSTART" not in v or not v.get("SUMMARY"):
            continue
        title = clean(v["SUMMARY"])
        start, end = v["DTSTART"], v.get("DTEND")
        all_day = bool(v.get("DTSTART_IS_DATE"))
        if all_day and end:
            end = end - timedelta(minutes=1)
        span = (end.date() - start.date()).days if end else 0
        cats = v.get("CATEGORIES", "")
        text = f"{title} {cats}"
        category = "other" if re.search(r"workshop|tour\b(?! and talk)|game", text, re.I) else \
            "film" if re.search(r"screening|film", text, re.I) else \
            "talk" if re.search(r"talk|lecture|reading|lezing|conversation|panel|book", text, re.I) else \
            guess_category(text, "other")
        out.append(Event(
            id=make_id(NAME, v.get("UID", title).split("@")[0]),
            title=title,
            subtitle=clean(cats) or None,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            all_day=all_day,
            url=v.get("URL") or HOMEPAGE,
            category=category,
            kind="series" if span >= 3 else "event",  # exhibitions run for weeks
        ))
    return out
