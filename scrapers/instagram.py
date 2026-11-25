"""Events read from Instagram posters (instagram/events.json, no network).

Posts are fetched weekly through the official Graph API (instagram/fetch.py, GitHub Action
'instagram.yml'); a scheduled Claude task reads caption + poster and writes the events here
(procedure: instagram/PROCESS.md). Hand edits are fine.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path

from .base import CATEGORIES, Event, clean, local, make_id

NAME = "instagram"
VENUE = "Instagram"
HOMEPAGE = "https://github.com/danielschaaf341/amsterdam-agenda/blob/main/instagram/events.json"
FILE = Path(__file__).resolve().parent.parent / "instagram" / "events.json"
MAY_BE_EMPTY = True  # weeks without Instagram events are normal


def fetch(client, today: date) -> dict:
    return json.loads(FILE.read_text(encoding="utf-8"))


def _dt(value: str) -> tuple[datetime, bool]:
    """'2026-11-25T20:00' → local datetime; '2026-11-25' → all-day."""
    if "T" in value:
        return local(datetime.fromisoformat(value)), False
    return local(datetime.combine(date.fromisoformat(value), time(0, 0))), True


def parse(raw: dict, today: date) -> list[Event]:
    out = []
    for item in raw.get("events", []):
        start, all_day = _dt(item["start"])
        end = _dt(item["end"])[0] if item.get("end") else None
        if all_day and end:
            end = end.replace(hour=23)
        category = item.get("category", "other")
        out.append(Event(
            id=make_id(NAME, str(item["id"])),
            title=clean(item["title"]),
            subtitle=clean(item.get("subtitle") or "") or None,
            venue=item["venue"],
            start=start,
            end=end if end and end > start else None,
            all_day=all_day,
            url=item.get("url") or HOMEPAGE,
            category=category if category in CATEGORIES else "other",
            price=item.get("price"),
            status=item.get("status", "normal"),
            kind="series" if end and (end.date() - start.date()).days >= 2 else "event",
        ))
    return out
