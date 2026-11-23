"""Tolhuistuin – its own programme (talks, workshops, markets, club nights, exhibitions).

Source: the agenda page embeds all items as HTML-escaped JSON in `:all-items='[...]'`
(eventStartDate 'YYYY/MM/DD HH:MM:SS' local, eventType.label, ticketPrice, freeEvent, soldOut, location,
paradisoEvent). Concerts with paradisoEvent=true are skipped: they come in via the Paradiso scraper.
'Doorlopend' = recurring sessions (same uid) → folded by collapse_recurring.
"""
from __future__ import annotations

import html as htmllib
import json
import re
from datetime import date, datetime

from .base import Event, clean, collapse_recurring, guess_category, local, make_id

NAME = "tolhuistuin"
VENUE = "Tolhuistuin"
HOMEPAGE = "https://tolhuistuin.nl/agenda"
TYPE_CATEGORY = {"muziek": "music", "clubnacht": "club", "talk": "talk", "theater": "theatre", "film": "film",
                 "workshop": "other", "overig": "other", "natuur": "other", "kunst": "other", "eten": "food",
                 "food": "food", "markt": "other"}


def fetch(client, today: date) -> list[dict]:
    page = client.get_text(HOMEPAGE)
    m = re.search(r":all-items='(\[.*?\])'", page, re.S)
    if not m:
        raise ValueError("no :all-items JSON on Tolhuistuin agenda page")
    return json.loads(htmllib.unescape(m.group(1)))


def _dt(value: str | None) -> datetime | None:
    return local(datetime.strptime(value, "%Y/%m/%d %H:%M:%S")) if value else None


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for d in raw:
        if d.get("paradisoEvent"):
            continue
        start, end = _dt(d.get("eventStartDate")), _dt(d.get("eventEndDate"))
        if not start:
            continue
        label = ((d.get("eventType") or {}).get("label") or "").strip()
        title = clean(d.get("title"))
        ongoing = label.lower() == "doorlopend"
        category = TYPE_CATEGORY.get(label.lower()) or guess_category(f"{title} {d.get('description') or ''}")
        price = "gratis" if d.get("freeEvent") else (
            "€ " + f"{float(d['ticketPrice']):.2f}".replace(".", ",").removesuffix(",00")
            if isinstance(d.get("ticketPrice"), (int, float)) and d["ticketPrice"] > 0 else None)
        out.append(Event(
            id=make_id(NAME, f"{d.get('uid') or title}-{start:%Y%m%d%H%M}"),
            title=title,
            subtitle=" · ".join(x for x in (clean(d.get("description")), clean(d.get("location"))) if x) or None,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            url=d.get("url") or HOMEPAGE,
            category=category if category != "other" or not ongoing else guess_category(title, "other"),
            status="sold_out" if d.get("soldOut") else "normal",
            price=price,
            image=((d.get("headerImages") or [{}])[0] or {}).get("url"),
        ))
    # 'Doorlopend' = recurring sessions sharing one uid (The Space Choir, …) → fold runs into one series
    return collapse_recurring(out, NAME)
