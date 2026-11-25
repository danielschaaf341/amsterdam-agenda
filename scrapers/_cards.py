"""Generic parser for agenda pages made of repeated 'cards' (one element per event).

Many small venues have no feed, just HTML cards with a title, a link and a date somewhere in the text:
'donderdag 26 november 2026 20:15', 'vr 27 nov | 16:45 - 01:00', 'Datum: 24 november Tijd: 9:15 pm',
'Su@Boom • November 29, 2026'. Each venue module only supplies a CSS selector (+ optional title selector).

fetch_cards() keeps only the card HTML (small fixtures); parse_cards() is pure.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import Event, clean, guess_category, infer_year, local, make_id, month_number

MONTHS = (r"januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december|"
          r"january|february|march|april|may|june|july|august|september|october|november|december|"
          r"jan|feb|mrt|mar|apr|jun|jul|aug|sep|sept|okt|oct|nov|dec")
DATE_DM = re.compile(rf"\b(\d{{1,2}})(?:e|st|nd|rd|th)?\s+({MONTHS})\.?(?:\s+(20\d\d))?\b", re.I)
DATE_MD = re.compile(rf"\b({MONTHS})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?(?:\s+(20\d\d))?\b", re.I)
DATE_NUM = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})(?:[/.-](20\d\d))?\b")
TIME = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\s*(am|pm|uur|u\b)?", re.I)


def fetch_cards(client, url: str, selector: str, render: bool = False, **render_kw) -> str:
    html = client.render(url, **render_kw) if render else client.get_text(url)
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(selector)
    if not cards:
        raise RuntimeError(f"no cards '{selector}' on {url}")
    for c in cards:
        for t in c.select("script, style, svg, noscript"):
            t.decompose()
    return "\n".join(f'<div class="__card" data-base="{url}">{c}</div>' for c in cards)


def find_date(text: str, today: date, numeric: bool = False) -> date | None:
    for rx, order in ((DATE_DM, "dm"), (DATE_MD, "md")):
        m = rx.search(text)
        if m:
            if order == "dm":
                day, mon, year = int(m.group(1)), m.group(2), m.group(3)
            else:
                mon, day, year = m.group(1), int(m.group(2)), m.group(3)
            try:
                month = month_number(mon)
                return date(int(year), month, day) if year else infer_year(day, month, today)
            except ValueError:
                continue
    if numeric:
        m = DATE_NUM.search(text)
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            try:
                return date(int(m.group(3)), month, day) if m.group(3) else infer_year(day, month, today)
            except ValueError:
                return None
    return None


def find_range(text: str, today: date) -> tuple[date | None, date | None]:
    """'13 Nov – 20 Dec 2026' / 'Wo 25 november - Do 26 november' → (start, end); single date → (d, None)."""
    hits = []
    for rx, order in ((DATE_DM, "dm"), (DATE_MD, "md")):
        for m in rx.finditer(text):
            hits.append((m.start(), m.end(), order, m))
    hits.sort()
    if not hits:
        return None, None
    def to_date(h, year_hint=None):
        _, _, order, m = h
        day, mon, year = (int(m.group(1)), m.group(2), m.group(3)) if order == "dm" else (int(m.group(2)), m.group(1), m.group(3))
        month = month_number(mon)
        if year:
            return date(int(year), month, day)
        if year_hint:
            cand = date(year_hint, month, day)
            return cand
        return infer_year(day, month, today)
    try:
        first = to_date(hits[0])
    except ValueError:
        return find_date(text, today), None
    if len(hits) > 1:
        gap = text[hits[0][1]:hits[1][0]]
        if len(gap) <= 16 and re.search(r"[–—-]|\bt/m\b|\btot\b|\bto\b|\buntil\b", gap):
            try:
                end = to_date(hits[1])
                if not hits[0][3].group(3) and hits[1][3].group(3):
                    # '13 Nov – 20 Dec 2026': the year belongs to both ends
                    first = to_date(hits[0], end.year if first.month <= end.month else end.year - 1)
                if end > first:
                    return first, end
            except ValueError:
                pass
    return first, None


def find_time(text: str) -> time | None:
    for m in TIME.finditer(text):
        h, mi, suffix = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower()
        if suffix == "pm" and h < 12:
            h += 12
        elif suffix == "am" and h == 12:
            h = 0
        return time(h, mi)
    return None


def parse_cards(raw: str, today: date, source: str, venue: str, *, title_sel: str | None = None,
                default_category: str = "other", numeric_dates: bool = False, category_fn=None,
                skip=None) -> list[Event]:
    out, seen = [], set()
    for wrap in BeautifulSoup(raw, "html.parser").select("div.__card"):
        base = wrap.get("data-base", "")
        card = next(wrap.children)
        text = clean(card.get_text(" | "))
        d, d_end = find_range(text, today)
        if not d and numeric_dates:
            d = find_date(text, today, True)
        if not d:
            continue
        # look for the time after the date when possible (titles can contain numbers)
        t = find_time(text)
        # first heading that isn't just a date ('donderdag 26 november', '24/11')
        title_el, title = None, ""
        for el in card.select(title_sel or "h1, h2, h3, h4, .title"):
            txt = clean(el.get_text(" "))
            if txt and not (len(txt) < 32 and (find_date(txt, today, True) or re.fullmatch(r"[\d/ .-]+", txt))):
                title_el, title = el, txt
                break
        if not title:
            continue
        # 'Pro Wrestling Holland! • November 27' → drop the trailing date
        title = re.sub(rf"\s*[•|–-]\s*(?:{MONTHS})\.?\s+\d{{1,2}}(?:,?\s+20\d\d)?\s*$", "", title, flags=re.I) or title
        if skip and skip(title, text):
            continue
        a = card if card.name == "a" and card.get("href") else (title_el.find_parent("a") if title_el else None) \
            or (title_el.select_one("a[href]") if title_el else None) or card.select_one("a[href]")
        url = urljoin(base, a["href"]) if a and a.get("href") else base
        key = (url, d, t)
        if key in seen:
            continue
        seen.add(key)
        low = text.lower()
        category = (category_fn(title, text) if category_fn else None) or guess_category(f"{title} {text[:200]}",
                                                                                         default_category)
        price = None
        if re.search(r"\bgratis\b|\bfree (entry|entrance|admission)\b|vrije toegang", low):
            price = "gratis"
        else:
            pm = re.search(r"€\s?\d+(?:[.,]\d{2})?", text)
            price = pm.group(0) if pm else None
        is_period = bool(d_end and (d_end - d).days >= 2)
        out.append(Event(
            id=make_id(source, f"{re.sub(r'[^a-z0-9]', '', url.lower())[-40:]}{d:%Y%m%d}{t or ''}"),
            title=title,
            venue=venue,
            start=local(datetime.combine(d, t or time(0, 0))),
            end=local(datetime.combine(d_end, time(23, 0))) if d_end else None,
            all_day=t is None,
            kind="series" if is_period else "event",
            url=url,
            category=category,
            status="cancelled" if re.search(r"\b(geannuleerd|afgelast|cancelled|canceled)\b", low)
            else "sold_out" if re.search(r"\b(uitverkocht|sold ?out|vol\b)", low) else "normal",
            price=price,
        ))
    return out
