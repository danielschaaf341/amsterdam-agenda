"""De Nieuwe Anita.

The homepage agenda grid turned out to be unstable (on 2026-11-23 it switched from ~65 upcoming
items to a 500-item archive sorted by day/month ignoring the year). So instead:

1. WP REST /wp/v2/agenda (newest 100 posts) gives the list of recent agenda items;
2. each detail page carries `_agenda_day` ('Sunday'), `_agenda_short_date` ('January 24'),
   `agenda_time_start` ('19:30') and `agenda_type` ('— Movie screening! —').
The weekday + day/month pins down the year exactly. ~100 detail requests per weekly run (cached).
Only the custom-field snippet of each detail page is kept (keeps fixtures small).
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timedelta

from bs4 import BeautifulSoup

from .base import Event, clean, guess_category, local, make_id, month_number, parse_hhmm

NAME = "nieuweanita"
VENUE = "De Nieuwe Anita"
HOMEPAGE = "https://denieuweanita.nl/"
API = "https://denieuweanita.nl/wp-json/wp/v2/agenda"
MAX_AGE_DAYS = 120
# recurring non-events (weekly haircut / knitting café); edit to taste
SKIP_TITLES = re.compile(r"timm knipt|fiber factory", re.I)  # skip detail pages of posts published longer ago than this

log = logging.getLogger(NAME)
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
FIELDS = ("_agenda_day", "_agenda_short_date", "agenda_time_start", "agenda_type")


def _snippet(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    for f in FIELDS:
        el = soup.select_one(f".post_custom_field.{f}")
        if el:
            out[f] = el.get_text(" ", strip=True)
    img = soup.select_one('meta[property="og:image"]')
    if img:
        out["image"] = img.get("content")
    return out


def fetch(client, today: date) -> list[dict]:
    posts = client.get_json(API, params={"per_page": 100, "_fields": "id,date,link,title,excerpt"})
    cutoff = today - timedelta(days=MAX_AGE_DAYS)
    items = []
    for p in posts:
        if date.fromisoformat(p["date"][:10]) < cutoff:
            continue
        try:
            fields = _snippet(client.get_text(p["link"]))
        except Exception as exc:  # one broken detail page shouldn't kill the venue
            log.warning("detail %s failed: %s", p["link"], exc)
            continue
        items.append({"id": p["id"], "link": p["link"], "title": p["title"]["rendered"],
                      "excerpt": clean(p["excerpt"]["rendered"])[:300], **fields})
    return items


def resolve_date(weekday: str, short_date: str, today: date) -> date | None:
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2})", short_date.strip())
    if not m:
        return None
    month, day = month_number(m.group(1)), int(m.group(2))
    wd = WEEKDAYS.index(weekday.strip().lower()) if weekday.strip().lower() in WEEKDAYS else None
    candidates = []
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            d = date(year, month, day)
        except ValueError:
            continue
        if wd is None or d.weekday() == wd:
            candidates.append(d)
    if not candidates:
        return None
    return min(candidates, key=lambda d: abs((d - today).days))


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for x in raw:
        if not x.get("_agenda_short_date"):
            continue
        d = resolve_date(x.get("_agenda_day", ""), x["_agenda_short_date"], today)
        if not d:
            log.warning("unparseable date for %s: %r", x["link"], x["_agenda_short_date"])
            continue
        try:
            t = parse_hhmm(x.get("agenda_time_start", ""))
        except ValueError:
            t = None
        title = clean(x["title"])
        if SKIP_TITLES.search(title) and not re.search(r"\+", title):
            continue
        kind = clean(x.get("agenda_type", "")).strip("— -")
        text = f"{title} {kind}"
        category = "film" if re.search(r"movie|film|cinema|screening", text, re.I) \
            else "theatre" if re.search(r"comedy|stand-?up|cabaret|theater|theatre", text, re.I) \
            else "jazz" if re.search(r"jazz", text, re.I) \
            else "club" if re.search(r"\bdj|dance|party|all night", text, re.I) \
            else "music" if re.search(r"\blive\b|acoustic|concert|band|gig|music|listening|singer|songwriter|blues|punk|rock",
                                      text, re.I) \
            else guess_category(text, "other")
        out.append(Event(
            id=make_id(NAME, x["id"]),
            title=title,
            subtitle=kind or None,
            venue=VENUE,
            start=local(datetime.combine(d, t or time(0, 0))),
            all_day=t is None,
            url=x["link"],
            category=category,
            status="cancelled" if re.search(r"cancel|afgelast", text, re.I)
            else "sold_out" if re.search(r"sold ?out|uitverkocht", text, re.I) else "normal",
            image=x.get("image"),
        ))
    return out
