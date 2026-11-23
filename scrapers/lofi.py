"""Lofi (club, Basisweg). Source: schema.org Event JSON-LD on lofi.amsterdam (dates only, no times)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time

from .base import Event, clean, local, make_id

NAME = "lofi"
VENUE = "Lofi"
HOMEPAGE = "https://lofi.amsterdam/"


def fetch(client, today: date) -> list[dict]:
    html = client.get_text(HOMEPAGE)
    events = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for x in data if isinstance(data, list) else data.get("@graph", [data]):
            if "Event" in str(x.get("@type")):
                events.append(x)
    if not events:
        raise RuntimeError("no Event JSON-LD on lofi.amsterdam")
    return events


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for e in raw:
        d = date.fromisoformat(e["startDate"][:10])
        has_time = len(e["startDate"]) > 10
        start = local(datetime.fromisoformat(e["startDate"])) if has_time else local(datetime.combine(d, time(0, 0)))
        offers = e.get("offers") or {}
        offers = offers[0] if isinstance(offers, list) and offers else offers
        avail = (offers.get("availability") or "").rsplit("/", 1)[-1]
        title = clean(e.get("name"))
        out.append(Event(
            id=make_id(NAME, f"{title}{d:%Y%m%d}"),
            title=title,
            venue=VENUE,
            start=start,
            all_day=not has_time,
            url=e.get("url") or offers.get("url") or HOMEPAGE,
            category="club",
            status="sold_out" if avail == "SoldOut" else "cancelled" if "Cancelled" in str(e.get("eventStatus")) else "normal",
            image=e.get("image") if isinstance(e.get("image"), str) else None,
        ))
    return out
