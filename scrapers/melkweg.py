"""Melkweg. Source: the full agenda embedded as JSON in __NEXT_DATA__ on /nl/agenda/ (one request)."""
from __future__ import annotations

import json
import re
from datetime import date

from .base import Event, clean, guess_category, make_id, parse_iso

NAME = "melkweg"
VENUE = "Melkweg"
HOMEPAGE = "https://www.melkweg.nl/nl/agenda/"

PROFILE_CATEGORY = {
    "concert": "music", "clubnacht": "club", "film": "film", "expositie": "other",
    "festival": "music", "theater": "theatre", "talk": "talk", "lezing": "talk",
}


def fetch(client, today: date) -> str:
    return client.get_text(HOMEPAGE)


def _initial_events(html: str) -> list[dict]:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("no __NEXT_DATA__ on Melkweg agenda page")
    data = json.loads(m.group(1))
    for block in data["props"]["pageProps"]["pageData"]["attributes"]["content"]:
        events = (block.get("attributes") or {}).get("initialEvents")
        if events:
            return events
    raise ValueError("no initialEvents block in Melkweg __NEXT_DATA__")


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for item in _initial_events(raw):
        a = item["attributes"]
        # NB: isPublished=False means "ticket sale closed" (sold out / cancelled), not hidden.
        if a.get("isPrivateEvent"):
            continue
        title = clean(a["name"])
        start = parse_iso(a.get("startTime") or a["startDate"])
        end = parse_iso(a["endDate"]) if a.get("endDate") else None
        if end and end < start:
            end = None
        profile = (a.get("profile") or "").lower()
        tags = " ".join(a.get("tags") or [])
        category = PROFILE_CATEGORY.get(profile) or guess_category(f"{title} {tags}")
        if "jazz" in tags.lower():
            category = "jazz"
        if a.get("isCancelled"):
            status = "cancelled"
        elif a.get("isMovedToNewDate"):
            status = "moved"
        elif a.get("isSoldOut"):
            status = "sold_out"
        else:
            status = "normal"
        images = (a.get("media") or {}).get("featuredImage") or []
        multi_day = bool(a.get("isMultiDayEvent")) and end and (end - start).days >= 2
        out.append(Event(
            id=make_id(NAME, item["id"]),
            title=title,
            subtitle=clean(a.get("artists")) or None,
            venue=VENUE,
            start=start,
            end=end,
            url="https://www.melkweg.nl" + a["url"],
            category=category,
            status=status,
            image=images[0]["filename"] if images else None,
            kind="series" if multi_day else "event",
        ))
    return out
