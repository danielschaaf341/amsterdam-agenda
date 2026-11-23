"""jazzin.amsterdam – jazz aggregator (Bimhuis, Kompaszaal, Zaal 100, Café de Pianist, Splendor, ...).

Source: the Next.js RSC payload on the homepage (`self.__next_f.push([1, "..."])` chunks) contains
clean event objects {calendar, title, date, time, venue, site, price, address, id, end_date, ...}.
The event's venue is the real venue (not 'jazzin'). ~1 month ahead.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time

from .base import Event, clean, local, make_id, parse_hhmm

NAME = "jazzin"
VENUE = "jazzin.amsterdam"
HOMEPAGE = "https://jazzin.amsterdam/"
# venues that have their own scraper → skip here to avoid near-duplicates with different titles
OWN_SCRAPER_VENUES = {"melkweg", "occii", "de nieuwe anita", "paradiso", "tolhuistuin", "bitterzoet",
                      "ot301", "de balie", "felix meritis", "rode hoed", "de rode hoed", "pakhuis de zwijger"}
# spelling variants seen in the feed
VENUE_ALIASES = {"theatercafé de richel": "Theater De Richel", "theater de richel": "Theater De Richel",
                 "cafe rivièra": "Café Rivièra", "café rivièra": "Café Rivièra"}


def fetch(client, today: date) -> str:
    return client.get_text(HOMEPAGE)


def _rsc_text(html: str) -> str:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\]\)', html)
    return "".join(json.loads(c) for c in chunks)


def extract_events(html: str) -> list[dict]:
    text = _rsc_text(html)
    dec = json.JSONDecoder()
    out, seen = [], set()
    for m in re.finditer(r'\{"calendar":"jazz', text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        if obj.get("id") in seen or not obj.get("date"):
            continue
        seen.add(obj.get("id"))
        out.append(obj)
    return out


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for o in extract_events(raw):
        venue = clean(o.get("venue")) or VENUE
        if venue.casefold() in OWN_SCRAPER_VENUES:
            continue
        venue = VENUE_ALIASES.get(venue.casefold(), venue)
        d = date.fromisoformat(o["date"][:10])
        try:
            t = parse_hhmm(o.get("time") or "")
        except ValueError:
            t = None
        start = local(datetime.combine(d, t or time(0, 0)))
        end = None
        if o.get("end_date"):
            try:
                end = local(datetime.combine(date.fromisoformat(o["end_date"][:10]), time(23, 59)))
            except ValueError:
                end = None
        title = clean(o.get("title"))
        price = clean(str(o.get("price") or "")) or None
        out.append(Event(
            id=make_id(NAME, o["id"]),
            title=title,
            subtitle=None,  # address omitted: the venue name is enough on a phone
            venue=venue,
            start=start,
            end=end if end and end > start else None,
            all_day=t is None,
            url=o.get("site") or HOMEPAGE,
            category="jazz",
            status="cancelled" if re.search(r"cancel|afgelast", title, re.I)
            else "sold_out" if re.search(r"sold ?out|uitverkocht", title, re.I) else "normal",
            price="gratis" if price and price.lower() in ("free", "gratis", "€0", "0") else price,
        ))
    return out
