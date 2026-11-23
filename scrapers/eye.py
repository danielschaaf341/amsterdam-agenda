"""Eye Filmmuseum – themed programmes (retrospectives, exhibitions with film series) as kind=series.

Source: the Next.js RSC payload of /whats-on: objects {"id","typeHandle":"programmeItem","title",
"supertitle","url","theme":[{"startDateTime","endDateTime"}]}. Individual screenings are not in the
server-rendered page and regular screenings aren't wanted anyway. 'Doorlopend' (ongoing) lines like
Eye Classics are skipped.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime

from .base import Event, clean, guess_category, local, make_id

NAME = "eye"
VENUE = "Eye Filmmuseum"
HOMEPAGE = "https://www.eyefilm.nl/whats-on"


def fetch(client, today: date) -> str:
    return client.get_text(HOMEPAGE)


def extract_items(html: str) -> list[dict]:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\]\)', html)
    text = "".join(json.loads(c) for c in chunks)
    dec, seen = json.JSONDecoder(), {}
    for m in re.finditer(r'\{"id":"\d+","typeHandle":"programmeItem"', text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        seen.setdefault(obj["id"], obj)
    return list(seen.values())


def _dt(value: str | None) -> datetime | None:
    return local(datetime.strptime(value[:16], "%Y-%m-%d %H:%M")) if value else None


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for o in extract_items(raw):
        supertitle = clean(o.get("supertitle"))
        if "doorlopend" in supertitle.lower():
            continue
        theme = (o.get("theme") or [{}])[0]
        start, end = _dt(theme.get("startDateTime")), _dt(theme.get("endDateTime"))
        if not start:
            continue
        images = o.get("image") or o.get("thumbnailImage") or []
        title = clean(o.get("title"))
        out.append(Event(
            id=make_id(NAME, o["id"]),
            title=title,
            subtitle=" · ".join(x for x in (supertitle, clean(o.get("subtitle"))) if x) or None,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            all_day=True,
            url=o.get("url") or HOMEPAGE,
            category=guess_category(f"{title} {supertitle}", "film") if "tentoonstelling" not in supertitle.lower()
            else "film",
            kind="series",
            image=images[0].get("url") if images else None,
        ))
    return out
