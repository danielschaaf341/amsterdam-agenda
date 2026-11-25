"""Het Ketelhuis (cinema, Westergas) – specials only.

1. RSS /feed/upcoming_events/ (Theater for WordPress) lists every upcoming screening; specials are
   recognisable by title: 'Queen at Sea | Film & Soep', '… + Q&A', '… | Voorpremière', 'Sneak Preview …',
   '… | Psychoanalyse & Film', '… | Cinebaby', 'Soirée Ciné | …', '… | Roze Filmdagen Monthly Special'.
2. Each special's page: 'Tickets en tijden | donderdag 26 november 2026 | 10:45 | …' → exact times.
Regular screenings are skipped (user preference).
"""
from __future__ import annotations

import html as htmllib
import logging
import re
from datetime import date, datetime, time

from bs4 import BeautifulSoup

from .base import Event, clean, local, make_id, month_number, parse_hhmm

NAME = "ketelhuis"
VENUE = "Het Ketelhuis"
HOMEPAGE = "https://www.ketelhuis.nl/specials/"
FEED = "https://www.ketelhuis.nl/feed/upcoming_events/"
SPECIAL = re.compile(r"\||q ?& ?a|voorpremi|preview|sneak|special|soir[eé]e|cinebaby|psychoanalyse|soep|"
                     r"inleiding|nagesprek|in gesprek|marathon|double bill|festival|idfa|studentenavond", re.I)
DATE_TIME = re.compile(r"(\d{1,2})\s+([a-z]+)\s+(20\d\d)\s*\|\s*(\d{1,2}:\d{2})", re.I)
MAX_DETAIL = 30

log = logging.getLogger(NAME)


def fetch(client, today: date) -> list[dict]:
    rss = client.get_text(FEED)
    seen, specials = set(), []
    for item in re.findall(r"<item>(.*?)</item>", rss, re.S):
        title = clean(htmllib.unescape(re.search(r"<title>(.*?)</title>", item, re.S).group(1)))
        link = re.search(r"<link>(.*?)</link>", item, re.S).group(1).strip()
        if not SPECIAL.search(title) or link in seen:
            continue
        seen.add(link)
        specials.append({"title": title, "link": link})
    out = []
    for s in specials[:MAX_DETAIL]:
        try:
            soup = BeautifulSoup(client.get_text(s["link"]), "html.parser")
            for t in soup(["script", "style", "svg"]):
                t.decompose()
            text = re.sub(r"(\s*\|\s*)+", " | ", soup.get_text("|"))
            seg = text.split("Tickets en tijden", 1)[-1].split("Alle films", 1)[0][:600]
            og = soup.select_one('meta[property="og:image"]')
            out.append({**s, "times": seg, "image": og.get("content") if og else None})
        except Exception as exc:
            log.warning("detail %s failed: %s", s["link"], exc)
    return out


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for s in raw:
        title = s["title"]
        if "save the date" in title.lower():
            continue
        for m in DATE_TIME.finditer(s.get("times") or ""):
            try:
                d = date(int(m.group(3)), month_number(m.group(2)), int(m.group(1)))
            except ValueError:
                continue
            t = parse_hhmm(m.group(4))
            left, _, right = (x.strip() for x in title.partition("|"))
            if right and SPECIAL.search(left) and not SPECIAL.search(right):
                left, right = right, left  # 'Soirée Ciné | Amelie' → film first
            subtitle = right or None
            out.append(Event(
                id=make_id(NAME, f"{s['link'].rstrip('/').rsplit('/', 1)[-1]}-{d:%Y%m%d}{t:%H%M}"),
                title=left if subtitle else title,
                subtitle=subtitle,
                venue=VENUE,
                start=local(datetime.combine(d, t)),
                url=s["link"],
                category="film",
                image=s.get("image"),
            ))
    return out
