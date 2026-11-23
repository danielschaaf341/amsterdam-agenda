"""ITA – Stadsschouwburg Amsterdam (incl. guest productions). Source: Nuxt payload of the agenda page.

/nl/agenda-stadsschouwburg?page=N → `events` (one per performance, with `program`:
startAt local, isCanceled, hasWaitingList, button.text, location) + pagination (32/page).
Every performance is its own event (user preference; set GROUP_RUNS=True to fold runs into a series).
"""
from __future__ import annotations

import html as htmllib
from collections import defaultdict
from datetime import date, datetime, timedelta

from ._nuxt import eval_nuxt
from .base import Event, clean, guess_category, is_run, local, make_id, run_span

NAME = "ita"
VENUE = "Stadsschouwburg (ITA)"
HOMEPAGE = "https://ita.nl/nl/agenda-stadsschouwburg"
BASE = "https://ita.nl"
MAX_PAGES = 8
GROUP_RUNS = False  # user wants every ITA performance in the list (not folded into one series)
GENRE_CATEGORY = {"muziek": "music", "jazz": "jazz", "talk": "talk", "perspectief": "talk", "expo": "other"}


def fetch(client, today: date) -> list[dict]:
    items, limit = [], today + timedelta(days=50)
    for page in range(1, MAX_PAGES + 1):
        data = eval_nuxt(client.get_text(HOMEPAGE, params={"page": page} if page > 1 else None))["data"]
        block = next(v for v in data.values() if isinstance(v, dict) and "events" in v)
        for e in block["events"]:
            p = e.get("program") or {}
            items.append({"id": e["id"], "url": e["url"], "title": e["title"], "subTitle": e.get("subTitle"),
                          "image": (e.get("image1") or {}).get("url"),
                          "genres": [g["name"] for g in e.get("genres") or []],
                          "attributes": [a["name"] for a in e.get("attributes") or []],
                          "program": {k: p.get(k) for k in ("id", "startAt", "endAt", "isCanceled", "hasWaitingList",
                                                              "button", "location")}})
        last = block["events"][-1].get("program", {}).get("startAt", "") if block["events"] else ""
        if page >= block["pagination"]["pages"] or (last and date.fromisoformat(last[:10]) > limit):
            break
    return items


def _status(p: dict) -> str:
    if p.get("isCanceled"):
        return "cancelled"
    if p.get("hasWaitingList") or "uitverkocht" in ((p.get("button") or {}).get("text") or "").lower():
        return "sold_out"
    return "normal"


def parse(raw: list[dict], today: date) -> list[Event]:
    by_prod: dict[str, list[dict]] = defaultdict(list)
    for x in raw:
        if (x.get("program") or {}).get("startAt"):
            by_prod[x["url"]].append(x)
    out, seen = [], set()
    for url, perfs in by_prod.items():
        perfs.sort(key=lambda x: x["program"]["startAt"])
        first = perfs[0]
        title = clean(htmllib.unescape(first["title"]))
        genres = first.get("genres") or []
        category = next((GENRE_CATEGORY[g.lower()] for g in genres if g.lower() in GENRE_CATEGORY), None) \
            or guess_category(f"{title} {' '.join(genres)}", "theatre")
        common = dict(subtitle=" · ".join(x for x in (clean(first.get("subTitle")), ", ".join(genres)) if x) or None,
                      venue=VENUE, url=BASE + url, category=category, image=first.get("image"))
        starts = [local(datetime.fromisoformat(x["program"]["startAt"])) for x in perfs]
        if GROUP_RUNS and is_run(starts):
            run_start, run_end = run_span(starts)
            out.append(Event(id=make_id(NAME, f"run{first['id']}"), title=title, start=run_start, end=run_end,
                             kind="series", **common))
            continue
        for x, start in zip(perfs, starts):
            p = x["program"]
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            end = local(datetime.fromisoformat(p["endAt"])) if p.get("endAt") else None
            out.append(Event(id=make_id(NAME, p["id"]), title=title, start=start,
                             end=end if end and end > start else None, status=_status(p), **common))
    return out
