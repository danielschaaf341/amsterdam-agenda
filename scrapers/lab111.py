"""LAB111 (cinema) – specials only.

1. WP REST posts in categories 'events' (116) and 'specials' (79): LAB Classics, double bills,
   anniversary parties, sing-alongs, festivals, film series.
2. Each post page has one `table#programmaNNN` per film with rows: 'zo 13 dec 12:00' | LAB 2 | SOLD OUT.
A post covering several films with >3 screenings becomes one kind=series (festival/retrospective);
otherwise every screening is its own event. The regular schedule is ignored.
NB: lab111.nl showed a "One moment, please…" bot page once → we keep requests low.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

from .base import Event, clean, guess_category, infer_year, local, make_id, month_number, parse_hhmm

# Disabled: lab111.nl answers our (honestly identified) bot user agent with a "One moment, please…"
# bot-check page. We don't work around that. Re-enable if LAB111 allows the agent (see RECON.md).
ENABLED = False
DISABLED_REASON = "site blokkeert scrapers met een bot-check"

NAME = "lab111"
VENUE = "LAB111"
HOMEPAGE = "https://www.lab111.nl/"
API = "https://www.lab111.nl/wp-json/wp/v2/posts"
CATEGORIES = "116,79"
MAX_AGE_DAYS = 90

log = logging.getLogger(NAME)


def _rows(html: str) -> list[dict]:
    if "One moment, please" in html[:2000]:
        raise RuntimeError("LAB111 served its bot-check page")
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for table in soup.select('table[id^="programma"]'):
        for tr in table.select("tr"):
            a = tr.select_one("a")
            if not a:
                continue
            rows.append({
                "table": table["id"],
                "when": a.get_text(" ", strip=True),
                "ticket": a.get("href"),
                "room": clean(tr.select_one(".theatre_name").get_text()) if tr.select_one(".theatre_name") else "",
                "note": clean(tr.get_text(" ")).replace(a.get_text(" ", strip=True), "").strip(),
            })
    img = soup.select_one('meta[property="og:image"]')
    return rows, (img.get("content") if img else None)


def fetch(client, today: date) -> list[dict]:
    posts = client.get_json(API, params={"categories": CATEGORIES, "per_page": 40,
                                         "_fields": "id,date,link,title,categories"})
    cutoff = today - timedelta(days=MAX_AGE_DAYS)
    out = []
    for p in posts:
        if date.fromisoformat(p["date"][:10]) < cutoff:
            continue
        try:
            rows, image = _rows(client.get_text(p["link"]))
        except Exception as exc:
            log.warning("post %s failed: %s", p["link"], exc)
            continue
        out.append({"id": p["id"], "link": p["link"], "title": p["title"]["rendered"],
                    "categories": p["categories"], "image": image, "rows": rows})
    return out


def parse_when(text: str, today: date) -> datetime:
    m = re.search(r"(\d{1,2})\s+([a-z]+)\.?\s+(\d{1,2}[:.]\d{2})", text.lower())
    if not m:
        raise ValueError(f"unparseable {text!r}")
    d = infer_year(int(m.group(1)), month_number(m.group(2)), today)
    return local(datetime.combine(d, parse_hhmm(m.group(3))))


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for post in raw:
        title = clean(post["title"])
        shows = []
        for r in post["rows"]:
            try:
                shows.append((parse_when(r["when"], today), r))
            except ValueError:
                continue
        if not shows:
            continue
        shows.sort(key=lambda s: s[0])
        films = {r["table"] for _, r in shows}
        category = guess_category(title, "film")
        if category not in ("film", "club", "music", "talk"):
            category = "film"
        if len(films) > 1 and len(shows) > 3:
            out.append(Event(
                id=make_id(NAME, f"series{post['id']}"),
                title=title,
                subtitle=f"{len(films)} films, {len(shows)} voorstellingen",
                venue=VENUE,
                start=shows[0][0],
                end=shows[-1][0],
                url=post["link"],
                category="film",
                kind="series",
                image=post.get("image"),
            ))
            continue
        for start, r in shows:
            note = r["note"].lower()
            out.append(Event(
                id=make_id(NAME, (r["ticket"] or "").rstrip("/").rsplit("/", 1)[-1] or f"{post['id']}{start:%m%d%H%M}"),
                title=title,
                subtitle=r["room"] or None,
                venue=VENUE,
                start=start,
                url=post["link"],
                category=category,
                status="sold_out" if "sold out" in note or "uitverkocht" in note else "normal",
                image=post.get("image"),
            ))
    return out
