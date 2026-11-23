"""FC Hyena (boutique cinema, Noord) – specials only.

Framer site. /films embeds a 'Specials' collection whose items link to /specials/<slug>
(e.g. 'Hyena Scream' baby screenings, monthly 'Sneak preview' by Amongst Friends). Each special page
states its next date(s) in prose: 'Maandag 30 november kun je genieten van PAPER TIGER! Aanvang 11.00'.
We parse those dates; regular screenings are skipped (user preference).
"""
from __future__ import annotations

import re
from datetime import date, datetime, time

from bs4 import BeautifulSoup

from .base import Event, clean, infer_year, local, make_id, month_number, parse_hhmm

NAME = "fchyena"
VENUE = "FC Hyena"
HOMEPAGE = "https://fchyena.nl/films"
DATE_RE = re.compile(r"(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+(\d{1,2})\s+"
                     r"(januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)",
                     re.I)
RULE_RE = re.compile(r"elke\s+(eerste|tweede|derde|vierde|laatste)\s+"
                     r"(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+van de maand", re.I)
ORDINALS = {"eerste": 1, "tweede": 2, "derde": 3, "vierde": 4, "laatste": -1}
WEEKDAYS = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
TIME_RE = re.compile(r"(?:aanvang|start|om|vanaf)\s*:?\s*(\d{1,2}[.:]\d{2})", re.I)


def _text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "svg"]):
        tag.decompose()
    return clean(soup.get_text(" "))


def fetch(client, today: date) -> list[dict]:
    films = client.get_text(HOMEPAGE)
    urls = sorted(set(re.findall(r"https://fchyena\.nl/specials/[a-z0-9-]+", films)))
    pages = []
    for url in urls:
        html = client.get_text(url)
        soup = BeautifulSoup(html, "html.parser")
        og = soup.select_one('meta[property="og:image"]')
        title = soup.select_one('meta[property="og:title"]')
        pages.append({"url": url, "title": title.get("content") if title else url.rsplit("/", 1)[-1],
                      "image": og.get("content") if og else None, "text": _text(html)[:4000]})
    return pages


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-th weekday (0=Monday) of a month; n=-1 is the last one."""
    import calendar
    days = [d for d in calendar.Calendar().itermonthdates(year, month) if d.month == month and d.weekday() == weekday]
    return days[n - 1] if n > 0 else days[-1]


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for p in raw:
        text = p["text"]
        slug = p["url"].rsplit("/", 1)[-1]
        name = slug.replace("-", " ").title()
        default_time = TIME_RE.search(text)
        rule = RULE_RE.search(text)
        if rule and not DATE_RE.search(text):
            # 'Elke derde dinsdag van de maand' → next three occurrences (time not stated)
            t = parse_hhmm(default_time.group(1)) if default_time else None
            for i in range(3):
                y, mth = today.year + (today.month - 1 + i) // 12, (today.month - 1 + i) % 12 + 1
                d = nth_weekday(y, mth, WEEKDAYS.index(rule.group(2).lower()), ORDINALS[rule.group(1).lower()])
                if d < today:
                    continue
                out.append(Event(
                    id=make_id(NAME, f"{slug}-{d:%Y%m%d}"),
                    title=f"{name}: sneak preview" if "sneak" in text.lower() else name,
                    subtitle=f"Elke {rule.group(1).lower()} {rule.group(2).lower()} van de maand",
                    venue=VENUE, start=local(datetime.combine(d, t or time(0, 0))), all_day=t is None,
                    url=p["url"], category="film", image=p.get("image"),
                ))
            continue
        for m in DATE_RE.finditer(text):
            d = infer_year(int(m.group(1)), month_number(m.group(2)), today)
            # a time in the sentence after the date wins over the page's general start time
            after = TIME_RE.search(text[m.end():m.end() + 200]) or default_time
            try:
                t = parse_hhmm(after.group(1)) if after else None
            except ValueError:
                t = None
            sentence = text[m.start(): m.start() + 160].split(". ")[0]
            film = re.search(r"(?:genieten van|vertonen we|draait|kijken we naar)\s+([^!.]{2,60})", sentence, re.I)
            out.append(Event(
                id=make_id(NAME, f"{p['url'].rsplit('/', 1)[-1]}-{d:%Y%m%d}"),
                title=f"{name}: {clean(film.group(1)).title()}" if film else name,
                venue=VENUE,
                start=local(datetime.combine(d, t or time(0, 0))),
                all_day=t is None,
                url=p["url"],
                category="film",
                image=p.get("image"),
            ))
    # same date mentioned twice on a page → keep one
    seen, unique = set(), []
    for e in out:
        if e.id not in seen:
            seen.add(e.id)
            unique.append(e)
    return unique
