"""De Balie. Source: WordPress REST (custom 'vo' field by the site's agency).

- /wp/v2/vo-programme: talks/debates; returns only upcoming items (36 on 2026-11-23)
- /wp/v2/vo-cinema: films; we only keep items with vo.special == True (CinéDialoog, CinéConcert, ...)
NB: vo.date_time_raw is labelled +00:00 but is actually local Amsterdam time.
"""
from __future__ import annotations

from datetime import date, datetime

from .base import Event, clean, guess_category, local, make_id, parse_hhmm, parse_iso

NAME = "debalie"
VENUE = "De Balie"
HOMEPAGE = "https://debalie.nl/programma/"
API = "https://debalie.nl/wp-json/wp/v2/"
FIELDS = "id,link,title,vo"


def fetch(client, today: date) -> dict:
    out = {}
    for kind in ("vo-programme", "vo-cinema"):
        items, page = [], 1
        while page <= 5:
            batch = client.get_json(f"{API}{kind}", params={"per_page": 100, "page": page, "_fields": FIELDS})
            items.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        out[kind] = items
    return out


def _status(vo: dict) -> str:
    st = (vo.get("status") or "").lower()
    if "cancel" in st or "geannuleerd" in st or "afgelast" in st:
        return "cancelled"
    if "sold" in st or "uitverkocht" in st or vo.get("available_tickets") == 0:
        return "sold_out"
    return "normal"


def _price(vo: dict) -> str | None:
    p = clean(vo.get("price_formatted") or (vo.get("price") if isinstance(vo.get("price"), str) else ""))
    if not p:
        return None
    return "gratis" if p.replace(" ", "") in ("€0,00", "€0") else p


def parse(raw: dict, today: date) -> list[Event]:
    out = []
    for item in raw.get("vo-programme", []):
        vo = item.get("vo") or {}
        if not vo.get("date_time_raw"):
            continue
        title = clean(item["title"]["rendered"])
        cat_text = clean(vo.get("category"))
        start = parse_iso(vo["date_time_raw"], assume_local=True)
        out.append(Event(
            id=make_id(NAME, item["id"]),
            title=title,
            subtitle=clean(vo.get("subtitle")) or None,
            venue=VENUE,
            start=start,
            all_day=not vo.get("time") and start.hour == 0 and start.minute == 0,
            url=item["link"],
            category="film" if cat_text.lower() == "cinema" else guess_category(f"{title} {cat_text}", "talk"),
            status=_status(vo),
            price=_price(vo),
            image=vo.get("featured_image") or None,
        ))
    for item in raw.get("vo-cinema", []):
        vo = item.get("vo") or {}
        if not vo.get("special"):
            continue  # regular screenings: skip (user only wants cinema specials)
        title = clean(item["title"]["rendered"])
        for day in vo.get("schedule") or []:
            d = datetime.strptime(day["day"], "%Y%m%d").date()
            for show in day.get("showtimes") or []:
                start = local(datetime.combine(d, parse_hhmm(show["time"])))
                out.append(Event(
                    id=make_id(NAME, show.get("program_id") or f"{item['id']}-{start:%Y%m%d%H%M}"),
                    title=title,
                    subtitle=clean(vo.get("subtitle")) or None,
                    venue=VENUE,
                    start=start,
                    url=item["link"],
                    category="film",
                    status=_status(vo),
                    price=_price(vo),
                    image=vo.get("featured_image") or None,
                ))
    return out
