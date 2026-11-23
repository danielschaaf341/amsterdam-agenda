"""Kriterion (cinema) – specials only, via Filmvandaag.

kriterion.nl is behind Cloudflare Turnstile (blocks scripts; we don't try to bypass it). Filmvandaag.nl
lists Kriterion's screenings (~a few days ahead) as schema.org Event JSON-LD. We keep only:
- titles/descriptions with special keywords (Sneak Preview, Q&A, voorpremière, marathon, ...)
- late-night screenings (start ≥ 23:00), Kriterion's midnight movies
Thin coverage by design; replace with a better source if Kriterion offers one.
"""
from __future__ import annotations

import json
import re
from datetime import date

from .base import Event, clean, make_id, parse_iso

NAME = "kriterion"
VENUE = "Kriterion"
HOMEPAGE = "https://www.kriterion.nl/"
SOURCE = "https://www.filmvandaag.nl/filmladder/23-kriterion-amsterdam"
SPECIAL = re.compile(r"sneak|preview|voorpremi|q ?& ?a|nagesprek|inleiding|marathon|double ?bill|special|"
                     r"kult|live score|quiz|sing[- ]?along|all[- ]?nighter", re.I)


def fetch(client, today: date) -> list[dict]:
    html = client.get_text(SOURCE)
    events = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for d in data if isinstance(data, list) else [data]:
            if d.get("@type") == "Event":
                events.append(d)
    if not events:
        raise RuntimeError("no Event JSON-LD on Filmvandaag page")
    return events


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for d in raw:
        if "kriterion" not in ((d.get("location") or {}).get("name") or "").lower():
            continue
        name = clean(d.get("name"))
        desc = clean(d.get("description"))
        start = parse_iso(d["startDate"])
        hit = SPECIAL.search(f"{name} {desc}")
        late = start.hour >= 23
        if not (hit or late):
            continue
        end = parse_iso(d["endDate"]) if d.get("endDate") else None
        out.append(Event(
            id=make_id(NAME, f"{name}{start:%Y%m%d%H%M}"),
            title=name if hit or "nacht" in name.lower() else f"{name} (late night)",
            subtitle=desc[:140] or None,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            url=d.get("url") or HOMEPAGE,
            category="film",
            status="cancelled" if "Cancelled" in (d.get("eventStatus") or "") else "normal",
            image=d.get("image"),
        ))
    return out
