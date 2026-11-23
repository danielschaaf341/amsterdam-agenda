"""De Brakke Grond (Vlaams Cultuurhuis). Source: HTML agenda cards + the public voordemensen ticket API.

Cards (a.card-default): date 'za 13 mrt' or a range 'zo 25 okt — wo 25 nov' (→ series), title, subtitle,
category. Times come from tickets.voordemensen.nl/api/debrakkegrond/events, matched on title + date.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time

from bs4 import BeautifulSoup

from .base import Event, clean, guess_category, infer_year, local, make_id, month_number, parse_hhmm

NAME = "brakkegrond"
VENUE = "De Brakke Grond"
HOMEPAGE = "https://brakkegrond.nl/agenda"
TICKETS = "https://tickets.voordemensen.nl/api/debrakkegrond/events"


def fetch(client, today: date) -> dict:
    soup = BeautifulSoup(client.get_text(HOMEPAGE), "html.parser")
    cards = [str(a) for a in soup.select("a.card-default[href*='/agenda/'], a.event-highlights__highlight")]
    try:
        tickets = client.get_json(TICKETS)
    except Exception:  # times are a bonus; the agenda works without them
        tickets = []
    shows = [{"name": s.get("event_name"), "date": s.get("event_date"), "time": s.get("event_time"),
              "soldout": s.get("event_soldout")} for m in tickets for s in m.get("sub_events") or []]
    return {"cards": cards, "shows": shows}


def _day(text: str, today: date) -> date | None:
    m = re.search(r"(\d{1,2})\s+([a-z]{3,})", text.lower())
    if not m:
        return None
    try:
        return infer_year(int(m.group(1)), month_number(m.group(2)), today)
    except ValueError:
        return None


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())[:20]


def parse(raw: dict, today: date) -> list[Event]:
    times = {}
    for s in raw.get("shows", []):
        if s.get("date") and s.get("time"):
            times.setdefault((s["date"], _key(s["name"])), s)
    out, seen = [], set()
    for html in raw["cards"]:
        a = BeautifulSoup(html, "html.parser").select_one("a")
        url = a["href"]
        if url in seen:
            continue
        seen.add(url)
        title_el = a.select_one(".card-default__title, .event-highlights__title")
        date_el = a.select_one(".card-default__date, .event-highlights__date")
        if not title_el or not date_el:
            continue
        title = clean(title_el.get_text(" "))
        sub_el = a.select_one(".card-default__subtitle, .event-highlights__subtitle")
        subtitle = clean(sub_el.get_text(" ")) if sub_el else ""
        cat_el = a.select_one(".card-default__category, .event-highlights__categories")
        cat_text = clean(cat_el.get_text(" ")) if cat_el else ""
        parts = [p for p in re.split(r"[—–-]{1,2}", clean(date_el.get_text(" "))) if p.strip()]
        first = _day(parts[0], today) if parts else None
        if not first:
            continue
        last = _day(parts[-1], today) if len(parts) > 1 else None
        if "residentie" in cat_text.lower():
            continue  # artists in residence (rehearsal period), not a public event
        name = f"{title}: {subtitle}" if subtitle else title
        show = times.get((first.isoformat(), _key(subtitle))) or times.get((first.isoformat(), _key(title)))
        t = parse_hhmm(show["time"]) if show else None
        start = local(datetime.combine(first, t or time(0, 0)))
        is_period = bool(last and (last - first).days >= 3)
        category = "theatre" if re.search(r"voorstelling|performance|dans|theater", cat_text, re.I) \
            else guess_category(f"{name} {cat_text}", "other")
        out.append(Event(
            id=make_id(NAME, url.rstrip("/").rsplit("/", 2)[-2] if "/agenda/" in url else url),
            title=name,
            subtitle=cat_text or None,
            venue=VENUE,
            start=start,
            end=local(datetime.combine(last, time(23, 0))) if is_period else None,
            all_day=t is None,
            url=url,
            category=category,
            kind="series" if is_period else "event",
            status="sold_out" if show and show.get("soldout") else "normal",
        ))
    return out
