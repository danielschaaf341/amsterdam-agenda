"""Thuishaven (open-air club / Loods, Noord). Source: HTML agenda accordion on thuishaven.nl.

Each .agenda-item: .qode-tab-title-inner '28 NOV | title', .agenda-details__date '28-11-2026', __times '13.00 – 23.00',
__price '€34,50' (or 'SOLD OUT'), genre class agenda-line-up--<genre>, 'Meer Info' link.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from .base import Event, clean, local, make_id, parse_hhmm

NAME = "thuishaven"
VENUE = "Thuishaven"
HOMEPAGE = "https://thuishaven.nl/"


def fetch(client, today: date) -> str:
    soup = BeautifulSoup(client.get_text(HOMEPAGE), "html.parser")
    items = soup.select(".agenda-item")
    if not items:
        raise RuntimeError("no agenda items on thuishaven.nl")
    return "\n".join(str(p) for p in items)


def parse(raw: str, today: date) -> list[Event]:
    out, seen = [], set()
    for p in BeautifulSoup(raw, "html.parser").select(".agenda-item"):
        d_el = p.select_one(".agenda-details__date")
        if not d_el:
            continue
        m = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", d_el.get_text())
        if not m:
            continue
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        times = clean(p.select_one(".agenda-details__times").get_text(" ")) if p.select_one(".agenda-details__times") else ""
        hhmm = re.findall(r"\d{1,2}[.:]\d{2}", times)
        start = local(datetime.combine(d, parse_hhmm(hhmm[0]))) if hhmm else local(datetime(d.year, d.month, d.day))
        end = local(datetime.combine(d, parse_hhmm(hhmm[1]))) if len(hhmm) > 1 else None
        heading = clean(p.select_one(".qode-tab-title-inner").get_text(" ")) if p.select_one(".qode-tab-title-inner") else ""
        title = re.sub(r"^\d{1,2}\s+[A-Z]{3}\s*", "", heading).strip(" |") or "Thuishaven"
        price_txt = clean(p.select_one(".agenda-details__price").get_text(" ")) if p.select_one(".agenda-details__price") else ""
        text = clean(p.get_text(" ")).lower()
        g = re.search(r"Genre:\s*([A-Za-z &/-]+?)\s+\d{1,2}-\d{1,2}-\d{4}", clean(p.get_text(" ")))
        genre = g.group(1).strip() if g else ""
        link = next((a["href"] for a in p.select("a[href]") if "meer info" in a.get_text(" ").lower()), HOMEPAGE)
        ev_id = make_id(NAME, f"{d:%Y%m%d}{re.sub(r'[^a-z0-9]', '', title.lower())[:20]}")
        if ev_id in seen:
            continue  # the page repeats some items
        seen.add(ev_id)
        out.append(Event(
            id=ev_id,
            title=title,
            subtitle=genre.title() or None,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            all_day=not hhmm,
            url=link,
            category="club",
            status="sold_out" if "sold out" in text or "uitverkocht" in text else "normal",
            price=price_txt if price_txt.startswith("€") else None,
        ))
    return out
