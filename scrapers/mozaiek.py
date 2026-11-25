"""Podium Mozaïek (theatre, music, comedy; Bos en Lommer). Source: the site's own JSON /api/events
(Ticketmatic sync): name, startts/endts (local), locationname (hall), custom_labels, ticket_url."""
from __future__ import annotations

from datetime import date, datetime

from .base import Event, clean, guess_category, local, make_id

NAME = "mozaiek"
VENUE = "Podium Mozaïek"
HOMEPAGE = "https://www.podiummozaiek.nl/programma/agenda"
API = "https://www.podiummozaiek.nl/api/events"
FIELDS = ("id", "name", "custom_titel", "custom_enegels", "startts", "endts", "locationname", "custom_status",
          "custom_labels", "ticket_url", "currentstatus")


def fetch(client, today: date) -> list[dict]:
    data = client.get_json(API, timeout=60)
    return [{k: e.get(k) for k in FIELDS} for e in data
            if str(e.get("startts") or "")[:10] >= (today.isoformat())]


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    for e in raw:
        if (e.get("custom_status") or "online") != "online" or not e.get("startts"):
            continue
        start = local(datetime.fromisoformat(e["startts"]))
        end = local(datetime.fromisoformat(e["endts"])) if e.get("endts") else None
        title = clean(e.get("name") or e.get("custom_titel"))
        performer = clean(e.get("custom_titel") or e.get("custom_enegels"))
        maker = performer if performer and performer.lower() not in title.lower() else ""
        labels = e.get("custom_labels")
        label_txt = labels if isinstance(labels, str) else ""
        out.append(Event(
            id=make_id(NAME, e["id"]),
            title=title,
            subtitle=" · ".join(x for x in (maker, label_txt, clean(e.get("locationname"))) if x) or None,
            venue=VENUE,
            start=start,
            end=end if end and end > start else None,
            url=e.get("ticket_url") or HOMEPAGE,
            category=guess_category(f"{title} {maker} {label_txt}", "theatre"),
            status="cancelled" if str(e.get("currentstatus")) in ("3", "cancelled") else "normal",
        ))
    return out
