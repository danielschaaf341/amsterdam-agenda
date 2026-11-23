"""Shared reader for Radar (radar.squat.net), filtered to ONE venue group.

The user declined Radar as a city-wide source (too noisy), but Vrankrijk's and Joe's Garage's own
websites show their Radar group agenda – so per-group it is simply the venue's own agenda.
API: /api/1.2/search/events.json?facets[group][]=<group nid>&limit=50&page=N
date_time[]: time_start/time_end with offset, optional rrule (→ kind="weekly").
"""
from __future__ import annotations

import re
from datetime import date

from .base import WEEKDAYS_NL, Event, clean, guess_category, make_id, parse_iso

API = "https://radar.squat.net/api/1.2/search/events.json"
FIELDS = "title,date_time,category,url,price,offline,uuid,body,event_status"
CATEGORY_MAP = {"food": "food", "music": "music", "concert": "music", "party": "club", "film": "film",
                "screening": "film", "discussion/presentation": "talk", "theater": "theatre", "theatre": "theatre",
                "bar/cafe": "other", "course/workshop": "other", "exhibition": "other", "(free) shop/market": "other",
                "action/protest/camp": "other", "work space/diy": "other"}
SKIP_CATEGORIES = {"advice/help/office hours", "meeting"}
RRULE_DAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def fetch_group(client, group_nid: int) -> list[dict]:
    items, page = [], 0
    while page < 6:
        data = client.get_json(API, params={"facets[group][]": group_nid, "limit": 50, "page": page,
                                            "fields": FIELDS})
        batch = list((data.get("result") or {}).values())
        items.extend(batch)
        if len(items) >= int(data.get("count") or 0) or len(batch) < 50:
            break
        page += 1
    for it in items:  # keep fixtures small
        it["body"] = clean((it.get("body") or {}).get("value") if isinstance(it.get("body"), dict) else "")[:300]
    return items


def parse_group(raw: list[dict], source: str, venue: str) -> list[Event]:
    out, seen = [], set()
    for e in raw:
        title = clean(e.get("title"))
        cats = [c.get("name", "").lower() for c in e.get("category") or []]
        if set(cats) & SKIP_CATEGORIES:
            continue
        text = f"{title} {e.get('body') or ''}"
        if re.search(r"\b(voku|vokü|volkskeuken|kitchen|keuken|dinner|diner|food)\b", title, re.I):
            category = "food"
        else:
            category = next((CATEGORY_MAP[c] for c in cats if c in CATEGORY_MAP), None) or guess_category(text)
        for dt in e.get("date_time") or []:
            start = parse_iso(dt["time_start"])
            end = parse_iso(dt["time_end"]) if dt.get("time_end") else None
            weekly = bool(dt.get("rrule"))
            # Radar stores each week of a recurring item as its own event → one weekly entry per title
            key = ("weekly", re.sub(r"[^a-z0-9]", "", title.lower())) if weekly else (e.get("uuid"), start)
            if key in seen:
                continue
            seen.add(key)
            subtitle = None
            if weekly:
                days = re.search(r"BYDAY=([A-Z,]+)", dt["rrule"])
                day_txt = ", ".join(WEEKDAYS_NL[RRULE_DAYS[d[-2:]]] for d in days.group(1).split(",")) if days else ""
                subtitle = f"Elke {day_txt} {start:%H:%M}".replace("  ", " ") if day_txt else f"Wekelijks {start:%H:%M}"
            out.append(Event(
                id=make_id(source, "weekly", title) if weekly else make_id(source, f"{e.get('uuid')}-{start:%Y%m%d%H%M}"),
                title=title,
                subtitle=subtitle,
                venue=venue,
                start=start,
                end=end if end and end > start and not weekly else None,
                all_day=start.hour == 0 and start.minute == 0 and not end,
                url=e.get("url") or "https://radar.squat.net/",
                category=category,
                kind="weekly" if weekly else "event",
                status="cancelled" if "cancel" in str(e.get("event_status") or "").lower() else "normal",
                price=clean(e.get("price") if isinstance(e.get("price"), str) else "") or None,
            ))
    return out
