"""Pakhuis de Zwijger. Source: HTML teaser cards on /agenda?page=N (WP REST is locked).

Card dates are relative or yearless: 'Vandaag, 20.00', 'Morgen, 19.00', 'do 26 nov, 19.30'.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

from .base import Event, clean, guess_category, infer_year, local, make_id, month_number, parse_hhmm

NAME = "zwijger"
VENUE = "Pakhuis de Zwijger"
HOMEPAGE = "https://dezwijger.nl/agenda"
BASE = "https://dezwijger.nl"
MAX_PAGES = 8

log = logging.getLogger(NAME)


def fetch(client, today: date) -> list[str]:
    pages = []
    for n in range(1, MAX_PAGES + 1):
        html = client.get_text(HOMEPAGE if n == 1 else f"{HOMEPAGE}?page={n}")
        if 'class="program-link"' not in html:
            break
        pages.append(html)
    return pages


def parse_when(text: str, today: date) -> datetime:
    text = clean(text).lower()
    t = parse_hhmm(text)
    if text.startswith("vandaag"):
        d = today
    elif text.startswith("morgen"):
        d = today + timedelta(days=1)
    elif text.startswith("overmorgen"):
        d = today + timedelta(days=2)
    else:
        m = re.search(r"(\d{1,2})\s+([a-z]+)\.?(?:\s+(\d{4}))?", text)
        if not m:
            raise ValueError(f"unparseable date {text!r}")
        day, month = int(m.group(1)), month_number(m.group(2))
        d = date(int(m.group(3)), month, day) if m.group(3) else infer_year(day, month, today)
    return local(datetime.combine(d, t))


def parse(raw: list[str], today: date) -> list[Event]:
    out, seen = [], set()
    for html in raw:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.program.teaser"):
            link = card.select_one("a.program-link")
            title_el = card.select_one(".title")
            when_el = card.select_one(".date-time")
            if not (link and title_el and when_el):
                continue
            href = link["href"]
            if href in seen:
                continue
            seen.add(href)
            try:
                start = parse_when(when_el.get_text(), today)
            except ValueError as exc:
                log.warning("skip %s: %s", href, exc)
                continue
            title = clean(title_el.get_text())
            sup = clean(card.select_one(".suptitle").get_text()) if card.select_one(".suptitle") else ""
            sub = clean(card.select_one(".subtitle").get_text()) if card.select_one(".subtitle") else ""
            sup = sup.rstrip(": ")
            if sup and sup.lower() not in title.lower():
                title = f"{sup}: {title}"
            card_text = clean(card.get_text()).lower()
            status = "normal"
            if re.search(r"\b(vol|uitverkocht|wachtlijst|sold out)\b", card_text):
                status = "sold_out"
            if re.search(r"\b(geannuleerd|afgelast|cancelled)\b", card_text):
                status = "cancelled"
            img = None
            source = card.select_one("picture source[srcset]")
            if source:
                img = source["srcset"].split()[0]
            loc = card.select_one(".location")
            out.append(Event(
                id=make_id(NAME, href.rstrip("/").rsplit("/", 1)[-1]),
                title=title,
                subtitle=" · ".join(x for x in (sub, clean(loc.get_text()) if loc else "") if x) or None,
                venue=VENUE,
                start=start,
                url=BASE + href if href.startswith("/") else href,
                category=guess_category(f"{title} {sub}", "talk"),
                status=status,
                image=img,
            ))
    return out
