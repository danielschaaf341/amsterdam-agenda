"""BIMHUIS (jazz, Piet Heinkade 3). Source: its own agenda HTML, /agenda?page=N (20 per page).

Tile: time.agenda-tile__dates[datetime=YYYY-MM-DD] 'do 26 november 2026' + <span>20:30</span>,
a.agenda-tile__link (h3 title), p (description), .agenda-tile__tags (series), button text
('tickets' / 'uitverkocht'), and labels like 'Gratis' / 'Laatste kaarten' in the text.
Replaces the jazzin listing for Bimhuis (jazzin only reaches ~1 month ahead).
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from bs4 import BeautifulSoup

from .base import Event, clean, local, make_id, parse_hhmm

NAME = "bimhuis"
VENUE = "Bimhuis"
HOMEPAGE = "https://www.bimhuis.nl/agenda"
MAX_PAGES = 4


def fetch(client, today: date) -> list[str]:
    pages, limit = [], today + timedelta(days=45)
    for n in range(1, MAX_PAGES + 1):
        soup = BeautifulSoup(client.get_text(HOMEPAGE, params={"page": n} if n > 1 else None), "html.parser")
        tiles = soup.select("li.agenda-tile-overview__item")
        for t in tiles:
            for tag in t.select("img, svg, figure"):
                tag.decompose()
        pages.append("\n".join(str(t) for t in tiles))
        dates = [t.select_one("time[datetime]")["datetime"] for t in tiles if t.select_one("time[datetime]")]
        if not tiles or (dates and date.fromisoformat(max(dates)[:10]) > limit):
            break
    return pages


def parse(raw: list[str], today: date) -> list[Event]:
    out, seen = [], set()
    for html in raw:
        for t in BeautifulSoup(html, "html.parser").select("li.agenda-tile-overview__item"):
            tm, link = t.select_one("time[datetime]"), t.select_one("a.agenda-tile__link")
            if not tm or not link:
                continue
            d = date.fromisoformat(tm["datetime"][:10])
            span = tm.select_one("span")
            try:
                start_t = parse_hhmm(span.get_text()) if span else None
            except ValueError:
                start_t = None
            url = link["href"]
            key = (url, d, start_t)
            if key in seen:
                continue
            seen.add(key)
            title = clean(link.get_text(" "))
            desc = clean(t.select_one("p").get_text(" ")) if t.select_one("p") else ""
            series = ", ".join(clean(a.get_text(" ")) for a in t.select(".agenda-tile__tags a"))
            text = clean(t.get_text(" ")).lower()
            out.append(Event(
                id=make_id(NAME, f"{url.rstrip('/').rsplit('/', 1)[-1]}-{d:%Y%m%d}{start_t or ''}"),
                title=title,
                subtitle=" · ".join(x for x in (desc, series) if x) or None,
                venue=VENUE,
                start=local(datetime.combine(d, start_t or time(0, 0))),
                all_day=start_t is None,
                url=url,
                category="jazz",
                status="cancelled" if re.search(r"\b(geannuleerd|afgelast|cancelled)\b", text)
                else "sold_out" if "uitverkocht" in text or "sold out" in text else "normal",
                price="gratis" if re.search(r"\bgratis\b", text) else None,
            ))
    return out
