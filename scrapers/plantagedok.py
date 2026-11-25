"""Plantage Dok (Dokhuis / Dokzaal, Plantage Doklaan). Source: The Events Calendar iCal feed.

'Dok Night' (Thursdays) are community dinners → food; the hall (Dokzaal / Dokhuis) goes in the subtitle.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from .base import Event, clean, guess_category, make_id, parse_ics

NAME = "plantagedok"
VENUE = "Plantage Dok"
HOMEPAGE = "https://plantagedok.nl/agenda/"
FEED = "https://plantagedok.nl/?post_type=tribe_events&ical=1&eventDisplay=list"


def fetch(client, today: date) -> str:
    return client.get_text(FEED)


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for v in parse_ics(raw):
        if "DTSTART" not in v or not v.get("SUMMARY"):
            continue
        title = clean(v["SUMMARY"])
        if re.search(r"\bstatement\b", title, re.I):
            continue
        start, end = v["DTSTART"], v.get("DTEND")
        all_day = bool(v.get("DTSTART_IS_DATE"))
        if all_day and end:
            end = end - timedelta(minutes=1)
        span = (end.date() - start.date()).days if end else 0
        text = f"{title} {v.get('CATEGORIES', '')}"
        category = "food" if re.search(r"dinner|diner|dok night|volkskeuken|kitchen|ferment", text, re.I) else \
            "film" if re.search(r"\bfilm|cinema|screening|documentar", text, re.I) else \
            guess_category(text, "other")
        hall = clean(v.get("LOCATION", "").split(",")[0]) or None
        out.append(Event(
            id=make_id(NAME, v.get("UID", title).split("@")[0]),
            title=title,
            subtitle=hall,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            all_day=all_day,
            url=v.get("URL") or HOMEPAGE,
            category=category,
            kind="series" if span >= 3 else "event",  # exhibitions run for weeks
        ))
    return out
