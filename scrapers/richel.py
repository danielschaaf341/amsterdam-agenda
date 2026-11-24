"""Theater De Richel (Nieuwezijds Voorburgwal 282). Replaces the (inaccurate) jazzin listing.

1. WP REST /wp/v2/evenementen (JetEngine): meta.begindatum / einddatum (unix, date only), uitverkocht,
   genre ids (names via /wp/v2/genre).
2. Detail page of each event in the window: '22:00 | GRATIS | Café' → start time, price, room.
"""
from __future__ import annotations

import html as htmllib
import logging
import re
from datetime import date, datetime, time, timedelta

from .base import TZ, Event, clean, local, make_id, parse_hhmm

NAME = "richel"
VENUE = "Theater De Richel"
HOMEPAGE = "https://theaterderichel.nl/agenda/"
API = "https://theaterderichel.nl/wp-json/wp/v2/"
WINDOW_DAYS = 50
log = logging.getLogger(NAME)

GENRE_CATEGORY = [("jazz", "jazz"), ("feest", "club"), ("dayrave", "club"), ("film", "film"),
                  ("comedy", "theatre"), ("stand-up", "theatre"), ("cabaret", "theatre"), ("kleinkunst", "theatre"),
                  ("toneel", "theatre"), ("theater", "theatre"), ("muziektheater", "theatre"), ("musical", "theatre"),
                  ("dans", "theatre"),
                  ("impro", "theatre"), ("mime", "theatre"), ("lezing", "talk"), ("literatuur", "talk"),
                  ("poëzie", "talk"), ("storytelling", "talk"), ("spoken word", "talk"), ("panel", "talk"),
                  ("politiek", "talk"), ("theatercollege", "talk"), ("salon", "talk"), ("muziek", "music"),
                  ("pop", "music"), ("klassiek", "music"), ("singer-songwriter", "music")]


def _day(ts) -> date | None:
    return datetime.fromtimestamp(int(ts), TZ).date() if ts else None


def fetch(client, today: date) -> dict:
    genres = {g["id"]: g["name"] for g in client.get_json(f"{API}genre", params={"per_page": 100, "_fields": "id,name"})}
    posts = []
    for page in (1, 2):
        batch = client.get_json(f"{API}evenementen", params={"per_page": 100, "page": page,
                                                              "_fields": "id,link,title,meta,genre"})
        posts.extend(batch)
        if len(batch) < 100:
            break
    events = []
    for p in posts:
        meta = p.get("meta") or {}
        d = _day(meta.get("begindatum"))
        end = _day(meta.get("einddatum")) or d
        if not d or end < today or d > today + timedelta(days=WINDOW_DAYS):
            continue
        try:
            page = client.get_text(p["link"])
            text = clean(re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " ", page, flags=re.S).replace("<", " <"))
            m = re.search(r"\b(\d{1,2}:\d{2})\s+(GRATIS|€\s*[\d.,]+(?:\s*[-–]\s*€?\s*[\d.,]+)?|UITVERKOCHT)?\s*"
                          r"(Café|Grote zaal|Kleine zaal|Zaal \w+)?", text)
            detail = {"time": m.group(1), "price": m.group(2), "room": m.group(3)} if m else {}
        except Exception as exc:
            log.warning("detail %s failed: %s", p["link"], exc)
            detail = {}
        events.append({"id": p["id"], "link": p["link"], "title": p["title"]["rendered"],
                       "begindatum": meta.get("begindatum"), "einddatum": meta.get("einddatum"),
                       "uitverkocht": meta.get("uitverkocht"),
                       "genres": [genres.get(g, "") for g in p.get("genre") or []], **detail})
    return events


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for e in raw:
        d, last = _day(e["begindatum"]), _day(e.get("einddatum"))
        try:
            t = parse_hhmm(e["time"]) if e.get("time") else None
        except ValueError:
            t = None
        genres_l = [g.lower() for g in e.get("genres") or []]
        category = next((cat for key, cat in GENRE_CATEGORY if key in genres_l), "other")
        price = e.get("price")
        out.append(Event(
            id=make_id(NAME, e["id"]),
            title=clean(htmllib.unescape(e["title"])),
            subtitle=" · ".join(x for x in (", ".join(e.get("genres") or []), e.get("room")) if x) or None,
            venue=VENUE,
            start=local(datetime.combine(d, t or time(0, 0))),
            end=local(datetime.combine(last, time(23, 0))) if last and (last - d).days >= 3 else None,
            all_day=t is None,
            url=e["link"],
            category=category,
            kind="series" if last and (last - d).days >= 3 else "event",
            status="sold_out" if str(e.get("uitverkocht")).lower() == "true" or (price or "").upper() == "UITVERKOCHT"
            else "normal",
            price="gratis" if (price or "").upper() == "GRATIS" else price if price and price.startswith("€") else None,
        ))
    return out
