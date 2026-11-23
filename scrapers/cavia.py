"""Filmhuis Cavia. Source: hand-written monthly pages /programma/<maand>-<jaar> (Concrete CMS).

Every item is a section after <hr id="anchor">: '<strong>Maandag 2 november, 18:30</strong>' then a label
(SPECIAL, DOCU, ...), optional <h3> series name and the <h2> title. Cavia is a volunteer filmhuis with
curated, one-off screenings, so every item counts as an event (not "regular screenings").
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime

from bs4 import BeautifulSoup
from requests import HTTPError

from .base import Event, clean, local, make_id, month_number, parse_hhmm

NAME = "cavia"
VENUE = "Filmhuis Cavia"
HOMEPAGE = "https://www.filmhuiscavia.nl/"
MONTHS_NL = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
             "oktober", "november", "december"]
DATE_RE = re.compile(r"(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)?\s*(\d{1,2})\s+"
                     r"([a-z]+)\s*,?\s*(\d{1,2}[:.]\d{2})", re.I)

log = logging.getLogger(NAME)


def month_urls(today: date, n: int = 2) -> list[tuple[str, int]]:
    out = []
    for i in range(n):
        m = (today.month - 1 + i) % 12
        y = today.year + (today.month - 1 + i) // 12
        out.append((f"{HOMEPAGE}programma/{MONTHS_NL[m]}-{y}", y))
    return out


def fetch(client, today: date) -> list[dict]:
    pages = []
    for url, year in month_urls(today):
        try:
            pages.append({"url": url, "year": year, "html": client.get_text(url)})
        except HTTPError as exc:  # next month's page often isn't online yet
            log.info("no page %s (%s)", url, exc.response.status_code if exc.response is not None else exc)
    if not pages:
        raise RuntimeError("no Cavia month pages found")
    return pages


def parse(raw: list[dict], today: date) -> list[Event]:
    out, seen = [], set()
    for page in raw:
        soup = BeautifulSoup(page["html"], "html.parser")
        for hr in soup.select("hr[id]"):
            anchor = hr["id"]
            # collect sibling elements until the next <hr>
            parts = []
            for sib in hr.find_next_siblings():
                if sib.name == "hr":
                    break
                parts.append(sib)
            block = BeautifulSoup("".join(str(p) for p in parts), "html.parser")
            text = clean(block.get_text(" "))
            m = DATE_RE.search(text)
            h2 = block.find("h2")
            if not m or not h2:
                continue
            try:
                month = month_number(m.group(2))
            except ValueError:
                continue
            year = page["year"] + (1 if month < today.month - 6 else 0)
            start = local(datetime.combine(date(year, month, int(m.group(1))), parse_hhmm(m.group(3))))
            title = clean(h2.get_text(" "))
            series = clean(block.find("h3").get_text(" ")) if block.find("h3") else ""
            label_m = re.search(r"\d{1,2}[:.]\d{2}\s+([A-Z][A-Z &/+-]{2,30})\b", text)
            label = label_m.group(1).strip().title() if label_m else ""
            if series and series.lower() not in title.lower():
                title = f"{series}: {title}"
            key = (title, start)
            if key in seen:
                continue
            seen.add(key)
            more = block.find("a", string=re.compile("MORE|MEER", re.I)) or block.find("a", href=re.compile("/programma/"))
            img = block.find("img")
            low = text.lower()
            out.append(Event(
                id=make_id(NAME, f"{anchor}-{start:%Y%m%d%H%M}"),
                title=title,
                subtitle=label or None,
                venue=VENUE,
                start=start,
                url=more["href"] if more and more.get("href", "").startswith("http") else f"{page['url']}#{anchor}",
                category="film",  # incl. live-score screenings
                status="cancelled" if re.search(r"\b(cancelled|geannuleerd|afgelast)\b", low)
                else "sold_out" if re.search(r"\b(sold out|uitverkocht)\b", low) else "normal",
                image=("https://www.filmhuiscavia.nl" + img["src"]) if img and img.get("src", "").startswith("/") else None,
            ))
    return out
