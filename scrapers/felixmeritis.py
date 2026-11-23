"""Felix Meritis. Source: the site's own JSON endpoint /wp-json/vo/v1/events?upcoming=true.

vo_date is yearless ('do 26 nov'); vo_time is free text ('19:30', '19.30', '8PM').
"""
from __future__ import annotations

import re
from datetime import date, datetime, time

from .base import Event, clean, guess_category, infer_year, local, make_id, month_number

NAME = "felixmeritis"
VENUE = "Felix Meritis"
HOMEPAGE = "https://felixmeritis.nl/programma/"
API = "https://felixmeritis.nl/wp-json/vo/v1/events"


def fetch(client, today: date) -> list[dict]:
    items, page = [], 1
    while page <= 10:
        data = client.get_json(API, params={"upcoming": "true", "per_page": 100, "page": page})
        items.extend(data.get("items") or [])
        if data.get("last_page", True):
            break
        page += 1
    return items


def parse_time(text: str) -> time | None:
    t = (text or "").strip().lower()
    m = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)", t)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
        return time(h, int(m.group(2) or 0))
    m = re.search(r"(\d{1,2})[:.](\d{2})", t)
    if m:
        return time(int(m.group(1)) % 24, int(m.group(2)))
    return None


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for x in raw:
        m = re.search(r"(\d{1,2})\s+([a-z]+)", (x.get("vo_date") or "").lower())
        if not m:
            continue
        d = infer_year(int(m.group(1)), month_number(m.group(2)), today)
        t = parse_time(x.get("vo_time"))
        title = clean(x.get("post_title"))
        out.append(Event(
            id=make_id(NAME, x["ID"]),
            title=title,
            subtitle=clean(x.get("post_excerpt"))[:160] or None,
            venue=VENUE,
            start=local(datetime.combine(d, t or time(0, 0))),
            all_day=t is None,
            url=f"https://felixmeritis.nl/programma/{x['post_name']}/",
            category=guess_category(f"{title} {x.get('post_excerpt', '')}", "talk"),
            image=x.get("vo_large_image") or None,
        ))
    return out
