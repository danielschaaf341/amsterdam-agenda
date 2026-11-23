"""Mezrab – The House of Stories (storytelling, comedy, music). Source: Events Manager iCal feed /events.ics."""
from __future__ import annotations

import re
from datetime import date

from .base import Event, clean, guess_category, make_id, parse_ics

NAME = "mezrab"
VENUE = "Mezrab"
HOMEPAGE = "https://mezrab.nl/"
FEED = "https://mezrab.nl/events.ics"


def fetch(client, today: date) -> str:
    return client.get_text(FEED)


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for v in parse_ics(raw):
        title = clean(v.get("SUMMARY"))
        text = f"{title} {v.get('CATEGORIES', '')}"
        if re.search(r"comedy|open mic|stand-?up|cabaret", text, re.I):
            category = "theatre"
        elif re.search(r"stor(y|ies)|verhal|book|lezing|talk|poetry|poëzie", text, re.I):
            category = "talk"
        else:
            category = guess_category(text, "music")
        end = v.get("DTEND")
        out.append(Event(
            id=make_id(NAME, v.get("UID", title).split("@")[0]),
            title=title,
            venue=VENUE,
            start=v["DTSTART"],
            end=end if end and end > v["DTSTART"] else None,
            url=v.get("URL") or HOMEPAGE,
            category=category,
            status="cancelled" if v.get("STATUS") == "CANCELLED" else "normal",
        ))
    return out
