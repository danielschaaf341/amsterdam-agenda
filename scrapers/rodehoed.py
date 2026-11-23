"""De Rode Hoed. Source: Inertia.js page JSON (<script data-page="app">) on /programma?page=N.

start_date is a date (as UTC midnight) + start_time 'HH:MM' local. status.value: sold_out, cancelled, ...
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time

from .base import Event, clean, guess_category, local, make_id, parse_hhmm

NAME = "rodehoed"
VENUE = "De Rode Hoed"
HOMEPAGE = "https://rodehoed.nl/programma/"
STATUS_MAP = {"sold_out": "sold_out", "waiting_list": "sold_out", "wachtlijst": "sold_out",
              "cancelled": "cancelled", "canceled": "cancelled", "moved": "moved", "postponed": "moved"}


def _programs(html: str) -> dict:
    m = re.search(r'<script data-page="app" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("no Inertia page JSON on Rode Hoed page")
    return json.loads(m.group(1))["props"]["programs"]


def fetch(client, today: date) -> list[dict]:
    items, page = [], 1
    while page <= 10:
        progs = _programs(client.get_text(HOMEPAGE, params={"page": page} if page > 1 else None))
        items.extend(progs["data"])
        if page >= progs["meta"]["last_page"]:
            break
        page += 1
    return items


def _price(p) -> str | None:
    if p in (None, ""):
        return None
    if float(p) == 0:
        return "gratis"
    return "€ " + (f"{float(p):.2f}".replace(".", ",").removesuffix(",00"))


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for p in raw:
        d = date.fromisoformat(p["start_date"][:10])
        t = parse_hhmm(p["start_time"]) if p.get("start_time") else None
        start = local(datetime.combine(d, t or time(0, 0)))
        end = None
        if p.get("end_date"):
            end = local(datetime.combine(date.fromisoformat(p["end_date"][:10]), time(23, 59)))
        title = clean(p["title"])
        topics = " ".join(t["name"] for t in p.get("topics") or [])
        status_value = ((p.get("status") or {}).get("value") or "").lower()
        img = (p.get("featured_image") or {}).get("url")
        out.append(Event(
            id=make_id(NAME, p["id"]),
            title=title,
            subtitle=clean(p.get("sub_title")) or None,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            all_day=t is None,
            url=p.get("detail_url") or HOMEPAGE,
            category="music" if re.search(r"\b(muziek|zingen|concert)\b", topics, re.I)
            else guess_category(f"{title} {topics}", "talk"),
            status=STATUS_MAP.get(status_value, "normal"),
            price=_price(p.get("price")),
            image=img,
        ))
    return out
