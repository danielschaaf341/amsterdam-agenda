"""SEXYLAND (Noord). Its NDSM theatre is being rebuilt (reopening autumn 2027); until then it lists the
occasional pop-up on sexyland.world, above a 'PAST EVENTS' block. We parse only the upcoming part:
'16 December 2026 | 19:00 - 22:30 | Café de Krom | Art Bar | BAS KOSTERS | …'.
"""
from __future__ import annotations

import re
from datetime import date, datetime

import html as htmllib

from .base import Event, clean, guess_category, local, make_id, month_number, parse_hhmm

NAME = "sexyland"
VENUE = "Sexyland"
HOMEPAGE = "https://sexyland.world/"
DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(20\d\d)\s*\|\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*\|\s*([^|]+)\|"
                     r"\s*([^|]+)\|\s*([^|]+)")


def clean_tags(html: str) -> str:
    return htmllib.unescape(re.sub(r"<[^>]+>", "|", html)).replace("\xa0", " ")


def fetch(client, today: date) -> str:
    html = client.get_text(HOMEPAGE)
    # (html.parser gives up on this 1 MB page, so strip tags with regexes)
    html = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " ", html, flags=re.S)
    text = re.sub(r"(\s*\|\s*)+", " | ", clean_tags(html))
    upcoming = text.split("PAST EVENTS")[0]
    return upcoming[-6000:]


def parse(raw: str, today: date) -> list[Event]:
    out = []
    for m in DATE_RE.finditer(raw):
        try:
            d = date(int(m.group(3)), month_number(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        place, kind, title = (clean(m.group(i)) for i in (6, 7, 8))
        start = local(datetime.combine(d, parse_hhmm(m.group(4))))
        end = local(datetime.combine(d, parse_hhmm(m.group(5))))
        out.append(Event(
            id=make_id(NAME, f"{d:%Y%m%d}{title}"),
            title=f"{title} ({kind})" if kind and kind.lower() not in title.lower() else title,
            subtitle=f"Sexyland pop-up @ {place}",
            venue=VENUE,
            start=start,
            end=end if end > start else None,
            url=HOMEPAGE,
            category=guess_category(f"{title} {kind}", "other"),
        ))
    return out
