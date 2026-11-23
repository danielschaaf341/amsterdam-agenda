"""Shared reader for WeTicket storefront RSS feeds (Skatecafé, Garage Noord, ...).

Each storefront (https://<org>.weticket.io/) links a public feed:
  https://api.weticket.io/storefront/organizations/<uuid>/events.xml
Items: title ('[SOLD OUT] …'), link, guid, ev:startdate / ev:enddate (UTC), ev:location,
description, media:content (image). No price or category → derived from title/time.
NB: the XML declaration claims utf-16 but the body is utf-8; we strip the declaration.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date

from .base import Event, clean, guess_category, make_id, parse_iso

NS = {"ev": "http://purl.org/rss/1.0/modules/event/", "media": "http://search.yahoo.com/mrss/"}
STATUS_RE = re.compile(r"^\s*\[(sold ?out|uitverkocht|cancelled|geannuleerd|afgelast|verplaatst|moved)\]\s*", re.I)


def feed_url(org_uuid: str) -> str:
    return f"https://api.weticket.io/storefront/organizations/{org_uuid}/events.xml"


def parse_feed(xml: str, source: str, venue: str) -> list[Event]:
    xml = re.sub(r"^\s*<\?xml[^>]*\?>", "", xml)
    root = ET.fromstring(xml)
    out = []
    for item in root.iter("item"):
        raw_title = clean(item.findtext("title"))
        status = "normal"
        m = STATUS_RE.match(raw_title)
        if m:
            word = m.group(1).lower()
            status = "sold_out" if word.startswith(("sold", "uitv")) else "moved" \
                if word.startswith(("verpl", "moved")) else "cancelled"
            raw_title = raw_title[m.end():]
        start = parse_iso(item.findtext("ev:startdate", namespaces=NS))
        end_txt = item.findtext("ev:enddate", namespaces=NS)
        end = parse_iso(end_txt) if end_txt else None
        desc = clean(item.findtext("description"))[:400]
        text = f"{raw_title} {desc}"
        if re.search(r"skateles|workshop|markt|market|lezing|quiz|kids", raw_title, re.I):
            category = guess_category(raw_title, "other")
        elif start.hour >= 22 or start.hour < 5 or re.search(r"\bdj\b|club ?night|all night|b2b", raw_title, re.I):
            category = "club"
        elif re.search(r"\blive\b|concert|band", raw_title, re.I):
            category = "music"
        else:
            category = guess_category(text, "music")
        media = item.find("media:content", NS)
        out.append(Event(
            id=make_id(source, item.findtext("guid")),
            title=raw_title,
            venue=venue,
            start=start,
            end=end if end and end > start else None,
            url=item.findtext("link"),
            category=category,
            status=status,
            image=media.get("url") if media is not None else None,
        ))
    return out
