"""Shared reader for Stager ticket shops: schema.org Event JSON-LD on https://<org>.stager.co/shop/<shop>.

Used by Nachbar and Radion. Items: name, startDate/endDate (with offset), url, eventStatus,
offers[].availability (SoldOut) and price.
"""
from __future__ import annotations

import json
import re
from datetime import date

from .base import Event, clean, guess_category, make_id, parse_iso


def fetch_shop(client, url: str) -> list[dict]:
    html = client.get_text(url)
    items = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        data = json.loads(block)
        for el in data.get("itemListElement", []) if isinstance(data, dict) else []:
            if (el.get("item") or {}).get("@type") == "Event":
                items.append(el["item"])
    if not items:
        raise RuntimeError(f"no Event JSON-LD on Stager shop {url}")
    return items


def parse_shop(raw: list[dict], source: str, venue: str, club: bool = True) -> list[Event]:
    out = []
    for e in raw:
        offers = e.get("offers") or []
        offers = offers if isinstance(offers, list) else [offers]
        avail = {(o.get("availability") or "").rsplit("/", 1)[-1] for o in offers}
        prices = sorted(float(o["price"]) for o in offers if o.get("price") not in (None, ""))
        status_url = (e.get("eventStatus") or "").rsplit("/", 1)[-1]
        status = "cancelled" if status_url == "EventCancelled" else "moved" \
            if status_url in ("EventPostponed", "EventRescheduled") else \
            "sold_out" if avail and avail <= {"SoldOut"} else "normal"
        start = parse_iso(e["startDate"])
        end = parse_iso(e["endDate"]) if e.get("endDate") else None
        title = clean(e.get("name"))
        fmt = lambda p: "€ " + f"{p:.2f}".replace(".", ",")
        late = start.hour >= 22 or start.hour < 5
        out.append(Event(
            id=make_id(source, e["url"].rstrip("/").rsplit("/", 1)[-1]),
            title=title,
            venue=venue,
            start=start,
            end=end if end and end > start else None,
            url=e["url"],
            category="club" if club and late else guess_category(title, "music"),
            status=status,
            price=(fmt(prices[0]) if prices[0] == prices[-1] else f"{fmt(prices[0])}–{fmt(prices[-1])}")
            if prices and prices[-1] > 0 else None,
            image=e.get("image") if isinstance(e.get("image"), str) else None,
        ))
    return out
