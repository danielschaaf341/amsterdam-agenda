"""Shared scraper for theatres on the 'Peppered' CMS: Theater Bellevue, De Kleine Komedie, Frascati.

These sites sit behind a BunnyCDN JavaScript check (plain HTTP gets a 307 to /csq/), which a normal
headless browser passes, so pages are rendered with Playwright (Client.render).

Agenda markup: li.eventCard (title, subtitle = company, supertitle, genres, price, link) with
li.subshow children (date 'wo 25 nov', time '12:30', button class status-wachtlijst / -uitverkocht).
Pagination: a.next → '?p54_page=2'.
A production with more than RUN_THRESHOLD performances close together (a theatre run) becomes one
kind=series; otherwise every performance is an event (monthly recurring shows stay events).
Exact datetimes come from `data-event-start` on order buttons when present.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import Event, clean, guess_category, infer_year, is_run, local, run_span, make_id, month_number, parse_hhmm

MAX_PAGES = 8
RUN_THRESHOLD = 4


def fetch_pages(client, agenda_url: str) -> list[str]:
    """Render agenda pages; return only the eventCard HTML of each page (keeps fixtures small)."""
    pages, url = [], agenda_url
    for _ in range(MAX_PAGES):
        html = client.render(url, wait_selector=".eventCard")
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("li.eventCard")
        if not cards:
            break
        pages.append("\n".join(str(c) for c in cards))
        nxt = soup.select_one("a.next[href]")
        if not nxt:
            break
        url = urljoin(agenda_url, nxt["href"].split("#")[0])
    if not pages:
        raise RuntimeError(f"no eventCards on {agenda_url}")
    return pages


def _day(text: str, today: date) -> date | None:
    m = re.search(r"(\d{1,2})\s+([a-z]{3,})", clean(text).lower())
    if not m:
        return None
    try:
        return infer_year(int(m.group(1)), month_number(m.group(2)), today)
    except ValueError:
        return None


def _price(card) -> str | None:
    values = []
    for td in card.select("td.price"):
        m = re.search(r"(\d+),(\d{2})", td.get_text())
        if m:
            values.append(float(f"{m.group(1)}.{m.group(2)}"))
    fmt = lambda v: "€ " + f"{v:.2f}".replace(".", ",")
    if values:
        lo, hi = min(values), max(values)
        return fmt(lo) if lo == hi else f"{fmt(lo)}–{fmt(hi)}"
    el = card.select_one(".meta .price")
    text = clean(el.get_text(" ")) if el else ""
    return text[:40] or None


OTHER_CITIES = re.compile(r"\b(den haag|rotterdam|utrecht|groningen|eindhoven|arnhem|nijmegen|maastricht|leiden|"
                          r"haarlem|tilburg|breda|zwolle|amersfoort|delft|deventer|antwerpen|gent|brussel|leuven)\b",
                          re.I)


def _is_here(sub, location_key: str, trust_class: bool) -> bool:
    """These sites also list a production's performances elsewhere (tours, sister venues)."""
    btn = sub.select_one("[data-event-location]")
    if btn and btn.get("data-event-location"):
        return location_key in btn["data-event-location"].lower()
    box = sub.select_one(".locationBox")
    if box:
        text = clean(box.get_text(" "))
        # tour dates read 'Theater Zuidplein, Rotterdam' / 'Podium Mozaiek, Amsterdam'
        if location_key not in text.lower() and (OTHER_CITIES.search(text) or re.search(r"\bAmsterdam\b", text)
                                                 or re.search(r"\w,\s*('s-)?[A-Z][\w-]+(\s[A-Z][\w-]+)?$", text)):
            return False
    classes = sub.get("class") or []
    if trust_class and "in-other-location" in classes:
        return False
    return True


def _performances(card, today: date, location_key: str = "", trust_class: bool = True
                  ) -> list[tuple[datetime, bool, str]]:
    """(start, all_day, status) per performance at this venue. Prefers exact data-event-start."""
    shows: dict[datetime, tuple[bool, str]] = {}
    for sub in card.select("li.subshow") or [card]:
        if location_key and not _is_here(sub, location_key, trust_class):
            continue
        btn = sub.select_one("[data-event-start]")
        if btn:
            start = local(datetime.fromisoformat(btn["data-event-start"]))
            shows[start] = (False, _status(sub))
            continue
        d_el = sub.select_one(".date .start") or sub.select_one(".top-date .start")
        d = _day(d_el.get_text() if d_el else "", today)
        if not d:
            continue
        t_el = sub.select_one(".time .start") or sub.select_one(".time")
        try:
            t = parse_hhmm(t_el.get_text()) if t_el else None
        except ValueError:
            t = None
        start = local(datetime.combine(d, t or time(0, 0)))
        shows.setdefault(start, (t is None, _status(sub)))
    return sorted((k, v[0], v[1]) for k, v in shows.items())


def _status(sub) -> str:
    cls = " ".join(" ".join(a.get("class", [])) for a in sub.select("a, span, div")).lower()
    txt = clean(sub.get_text(" ")).lower()
    if "geannuleerd" in cls or "afgelast" in txt or "geannuleerd" in txt:
        return "cancelled"
    if "verplaatst" in cls or "verplaatst" in txt:
        return "moved"
    if re.search(r"status-(wachtlijst|uitverkocht|soldout)", cls) or "uitverkocht" in txt:
        return "sold_out"
    return "normal"


GENRE_CATEGORY = {"theater": "theatre", "toneel": "theatre", "dans": "theatre", "cabaret": "theatre",
                  "comedy": "theatre", "muziek": "music", "muziektheater": "theatre", "jazz": "jazz",
                  "klassiek": "music", "talk": "talk", "lezing": "talk", "film": "film", "club": "club",
                  "performance": "theatre", "familie": "theatre", "jeugd": "theatre", "opera": "theatre"}


def parse_pages(pages: list[str], today: date, source: str, venue: str, base_url: str,
                location_key: str = "", trust_class: bool = True) -> list[Event]:
    out, seen = [], set()
    for html in pages:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("li.eventCard"):
            entry = card.get("data-entry-id")
            if entry in seen:
                continue
            seen.add(entry)
            title_el = card.select_one(".title")
            link = card.select_one("a.desc[href]") or card.select_one("a[href]")
            if not title_el or not link:
                continue
            title = clean(title_el.get_text(" "))
            company = clean(card.select_one(".subtitle").get_text(" ")) if card.select_one(".subtitle") else ""
            supertitle = clean(card.select_one(".supertitle").get_text(" ")) if card.select_one(".supertitle") else ""
            genres = [clean(g.get_text()) for g in card.select(".genres__link")]
            price = _price(card)
            url = urljoin(base_url, link["href"])
            img = card.select_one("img[src]")
            category = next((GENRE_CATEGORY[g.lower()] for g in genres if g.lower() in GENRE_CATEGORY), None) \
                or guess_category(f"{title} {supertitle} {' '.join(genres)}", "theatre")
            subtitle = " · ".join(x for x in (company, supertitle) if x) or None

            shows = _performances(card, today, location_key, trust_class)
            if not shows:
                continue
            shows.sort()
            common = dict(subtitle=subtitle, venue=venue, url=url, category=category, price=price,
                          image=img["src"] if img else None)
            if is_run([st for st, _, _ in shows], RUN_THRESHOLD):
                statuses = {s for _, _, s in shows}
                first, last = run_span([st for st, _, _ in shows])
                out.append(Event(
                    id=make_id(source, f"run{entry}"), title=title, start=first, end=last,
                    kind="series", status="sold_out" if statuses == {"sold_out"} else "normal", **common))
                continue
            for start, all_day, status in shows:
                out.append(Event(id=make_id(source, f"{entry}-{start:%Y%m%d%H%M}"), title=title, start=start,
                                 all_day=all_day, status=status, **common))
    return out
