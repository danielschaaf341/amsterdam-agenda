"""Rialto (De Pijp + Silo) – specials only. Source: Nuxt payload of /nl/specials/<slug> pages.

The specials overview links to themed pages (film series, voorpremières, ...). Each page's payload has
`events` (films) with `programs` (screenings: startAt local, location, isCanceled, button.text, attributes).
- a film series (several films) → one kind=series spanning first..last screening
- voorpremières and screenings 'met inleiding' / Q&A / nagesprek → individual events
- kinderfilms are skipped (regular programming)
"""
from __future__ import annotations

import html as htmllib
import re
from datetime import date, datetime

from ._nuxt import eval_nuxt
from .base import Event, clean, local, make_id

NAME = "rialto"
VENUE = "Rialto"
HOMEPAGE = "https://depijp.rialtofilm.nl/nl/specials"
BASE = "https://depijp.rialtofilm.nl"
SKIP_SLUGS = {"kinderfilms"}
# standing programme lines: not a time-limited series; only their special screenings are kept
NOT_SERIES = {"klassiek"}
EVENT_ATTRS = re.compile(r"voorpremi|inleiding|q ?& ?a|nagesprek|gesprek|special|live|premi[eè]re", re.I)


def fetch(client, today: date) -> list[dict]:
    overview = client.get_text(HOMEPAGE)
    slugs = sorted(set(re.findall(r'href="/nl/specials/([a-z0-9-]+)"', overview)) - SKIP_SLUGS)
    pages = []
    for slug in slugs:
        data = eval_nuxt(client.get_text(f"{BASE}/nl/specials/{slug}"))["data"]
        page = next((v for v in data.values() if isinstance(v, dict) and str(v.get("_url", "")).startswith("/nl/specials")), {})
        films = next((v["events"] for v in data.values() if isinstance(v, dict) and "events" in v), [])
        pages.append({
            "slug": slug,
            "title": (page.get("content") or {}).get("title") or slug,
            "image": ((page.get("content") or {}).get("imageObject") or {}).get("url"),
            "films": [{"id": f["id"], "title": f["title"], "url": f["url"],
                       "image": (f.get("image1") or {}).get("url"), "programs": f.get("programs") or []}
                      for f in films],
        })
    return pages


def _attrs(p: dict) -> list[str]:
    return [a.get("name", "") for a in p.get("attributes") or []]


def _venue(p: dict) -> str:
    loc = ((p.get("location") or {}).get("name") or "").lower()
    return "Rialto VU" if "vu" in loc or "griffioen" in loc else "Rialto Silo" if "silo" in loc else "Rialto De Pijp"


def _placeholder(p: dict) -> bool:
    """'verwacht' programs only carry a release date (00:00, location 'Onbekend.')."""
    return any(a.lower() == "verwacht" for a in _attrs(p))


def parse(raw: list[dict], today: date) -> list[Event]:
    out, seen = [], set()
    for page in raw:
        title = clean(htmllib.unescape(page["title"]))
        is_voorpremiere = bool(re.search(r"voorpremi", page["slug"]))
        is_series = len(page["films"]) > 1 and not is_voorpremiere and page["slug"] not in NOT_SERIES
        all_shows = sorted(((local(datetime.fromisoformat(p["startAt"])), f, p) for f in page["films"]
                            for p in f["programs"] if p.get("startAt")), key=lambda s: s[0])
        shows = [s for s in all_shows if not _placeholder(s[2])]
        if is_series and all_shows:
            span = shows or all_shows
            films = sorted({clean(f["title"]) for _, f, _ in all_shows})
            out.append(Event(
                id=make_id(NAME, f"series-{page['slug']}"),
                title=title,
                subtitle=f"{len(films)} films: " + ", ".join(films[:5]) + (" …" if len(films) > 5 else ""),
                venue=_venue(span[0][2]) if shows else "Rialto De Pijp",
                start=span[0][0],
                end=span[-1][0] if span[-1][0] > span[0][0] else None,
                all_day=not shows,
                url=f"{BASE}/nl/specials/{page['slug']}",
                category="film",
                kind="series",
                image=page.get("image"),
            ))
        for start, film, p in shows:
            if p["id"] in seen:
                continue  # same screening listed on two specials pages
            attrs = _attrs(p)
            special = [a for a in attrs if EVENT_ATTRS.search(a)]
            one_off_page = len(page["films"]) == 1  # e.g. 'Rialto for Short – de finale'
            if not special and not is_voorpremiere and not one_off_page:
                continue  # regular screening of a series / standing line
            seen.add(p["id"])
            label = special[0] if special else ("Voorpremière" if "voorpremi" in page["slug"] else "")
            ftitle = clean(htmllib.unescape(film["title"]))
            button = ((p.get("button") or {}).get("text") or "").lower()
            end = local(datetime.fromisoformat(p["endAt"])) if p.get("endAt") else None
            out.append(Event(
                id=make_id(NAME, p["id"]),
                title=f"{ftitle} ({label})" if label and label.lower() not in ftitle.lower() else ftitle,
                subtitle=title if is_series else None,
                venue=_venue(p),
                start=start,
                end=end if end and end > start else None,
                url=BASE + film["url"],
                category="film",
                status="cancelled" if p.get("isCanceled") else "sold_out" if "uitverkocht" in button
                or p.get("hasWaitingList") else "normal",
                image=film.get("image"),
            ))
    return out
