"""Fixed weekly items from recurring.json (no network): food nights etc. for places without an agenda.

E.g. De Sering (site behind Cloudflare, only Instagram) – its community kitchen runs Mon–Sat 18–21.
Each item becomes one kind="weekly" entry, shown under "Vaste prik" on the site.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .base import CATEGORIES, WEEKDAYS_NL, Event, local, make_id, parse_hhmm

NAME = "recurring"
VENUE = "Vaste prik (recurring.json)"
HOMEPAGE = "https://github.com/danielschaaf341/amsterdam-agenda/blob/main/recurring.json"
FILE = Path(__file__).resolve().parent.parent / "recurring.json"


def fetch(client, today: date) -> dict:
    return json.loads(FILE.read_text(encoding="utf-8"))


def parse(raw: dict, today: date) -> list[Event]:
    out = []
    for item in raw.get("items", []):
        days = [WEEKDAYS_NL.index(d.lower()[:2]) for d in item["weekdays"]]
        first = next(today + timedelta(days=i) for i in range(7) if (today + timedelta(days=i)).weekday() in days)
        t = parse_hhmm(item["start"])
        when = f"Elke {', '.join(WEEKDAYS_NL[d] for d in sorted(days))} {item['start']}" + \
               (f"–{item['end']}" if item.get("end") else "")
        category = item.get("category", "food")
        out.append(Event(
            id=make_id(NAME, item["venue"], item["title"]),
            title=item["title"],
            subtitle=" · ".join(x for x in (when, item.get("note")) if x),
            venue=item["venue"],
            start=local(datetime.combine(first, t)),
            end=local(datetime.combine(today + timedelta(days=42), t)),
            url=item.get("url") or HOMEPAGE,
            category=category if category in CATEGORIES else "other",
            kind="weekly",
        ))
    return out
