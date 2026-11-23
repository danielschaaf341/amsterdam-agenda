"""Café Voorwaarts (Schaafstraat 12, Noord). Source: The Events Calendar iCal subscription feed."""
from __future__ import annotations

from datetime import date, timedelta

from .base import Event, clean, guess_category, make_id, parse_ics

NAME = "cafevoorwaarts"
VENUE = "Café Voorwaarts"
HOMEPAGE = "https://cafevoorwaarts.nl/index.php/agenda/"
FEED = "https://cafevoorwaarts.nl/?post_type=tribe_events&ical=1&eventDisplay=list"
CATEGORY_MAP = {"expositie": "other", "muziek": "music", "live muziek": "music", "dj": "club", "film": "film",
                "lezing": "talk", "quiz": "other", "theater": "theatre", "jazz": "jazz"}


def fetch(client, today: date) -> str:
    return client.get_text(FEED)


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for v in parse_ics(raw):
        title = clean(v.get("SUMMARY"))
        cats = [c.strip().lower() for c in v.get("CATEGORIES", "").split(",") if c.strip()]
        category = next((CATEGORY_MAP[c] for c in cats if c in CATEGORY_MAP), None) or guess_category(title)
        start, end = v["DTSTART"], v.get("DTEND")
        all_day = bool(v.get("DTSTART_IS_DATE"))
        if all_day and end:
            end = end - timedelta(minutes=1)  # iCal all-day DTEND is exclusive
        multi_day = bool(end) and (end.date() - start.date()).days >= 1
        out.append(Event(
            id=make_id(NAME, v.get("UID", title).split("@")[0]),
            title=title,
            subtitle=", ".join(c.title() for c in cats) or None,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            all_day=all_day,
            url=v.get("URL") or HOMEPAGE,
            category=category,
            kind="series" if multi_day and all_day else "event",
            status="cancelled" if v.get("STATUS") == "CANCELLED" else "normal",
        ))
    return out
