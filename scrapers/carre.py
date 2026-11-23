"""Koninklijk Theater Carré. Source: the site's own JSON endpoint /api/render/production-page-list-nl.

`productions[id].events[]` (start_date/end_date with offset, sales_status, data.status, ticketsFree)
+ `nodes` of kind "production-page" (title, url, production_id, filters.genres).
Long runs (circus, musicals: is_run) → one kind="series"; other shows → individual events.
fetch() trims the ~2 MB response to the fields we use (keeps the fixture small).
"""
from __future__ import annotations

from datetime import date

from .base import Event, clean, is_run, make_id, parse_iso, run_span

NAME = "carre"
VENUE = "Carré"
HOMEPAGE = "https://carre.nl/agenda"
API = "https://carre.nl/api/render/production-page-list-nl"
GENRE_CATEGORY = {"concert_internationaal": "music", "concert_nationaal": "music", "comedy_international": "theatre",
                  "comedy_internationaal": "theatre", "cabaret": "theatre", "musical": "theatre", "toneel": "theatre",
                  "dans": "theatre", "ballet": "theatre", "opera": "theatre", "circus": "theatre",
                  "one(wo)_menshow": "theatre", "amusement": "theatre"}


def fetch(client, today: date) -> list[dict]:
    d = client.get_json(API, timeout=60)
    pages = {n["production_id"]: n for n in d["nodes"].values()
             if n.get("kind") == "production-page" and n.get("production_id")}
    out = []
    for pid, prod in d["productions"].items():
        page = pages.get(pid, {})
        pdata = page.get("data") or {}
        out.append({
            "id": pid,
            "name": (prod.get("data") or {}).get("name"),
            "title": pdata.get("title") or pdata.get("agendaTitle"),
            "url": pdata.get("url"),
            "genres": (page.get("filters") or {}).get("genres") or [],
            "events": [{"id": e["id"], "start_date": e["start_date"], "end_date": e.get("end_date"),
                        "sales_status": e.get("sales_status"),
                        "status": (e.get("data") or {}).get("status"),
                        "subtitle": (e.get("data") or {}).get("subtitle"),
                        "ticketsFree": (e.get("data") or {}).get("ticketsFree")}
                       for e in prod.get("events") or []],
        })
    return out


def _status(e: dict) -> str:
    text = f"{e.get('sales_status') or ''} {e.get('status') or ''}".lower()
    if "cancel" in text or "geannuleerd" in text or "afgelast" in text:
        return "cancelled"
    if "sold" in text or "uitverkocht" in text or e.get("ticketsFree") == 0:
        return "sold_out"
    return "normal"


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for p in raw:
        perfs = sorted(p["events"], key=lambda e: e["start_date"])
        if not perfs:
            continue
        title = clean(p.get("title") or p.get("name"))
        url = "https://carre.nl" + p["url"] if p.get("url") else HOMEPAGE
        category = next((GENRE_CATEGORY[g] for g in p["genres"] if g in GENRE_CATEGORY), "theatre")
        genre = ", ".join(g.replace("_", " ") for g in p["genres"]) or None
        starts = [parse_iso(e["start_date"]) for e in perfs]
        if is_run(starts):
            a, b = run_span(starts)
            out.append(Event(id=make_id(NAME, f"run{p['id']}"), title=title, subtitle=genre, venue=VENUE,
                             start=a, end=b, url=url, category=category, kind="series"))
            continue
        for e, start in zip(perfs, starts):
            end = parse_iso(e["end_date"]) if e.get("end_date") else None
            out.append(Event(id=make_id(NAME, e["id"]), title=title,
                             subtitle=clean(e.get("subtitle")) or genre, venue=VENUE, start=start,
                             end=end if end and end > start else None, url=url, category=category,
                             status=_status(e)))
    return out
