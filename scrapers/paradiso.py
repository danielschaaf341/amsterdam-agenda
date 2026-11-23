"""Paradiso (also covers Tolhuistuin and Bitterzoet via `location`).

Source: the GraphQL API the paradiso.nl site itself uses (public read token from the site's JS;
usage approved by the user). Paginated with `searchAfter` = the `sort` value of the last event.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .base import Event, clean, guess_category, make_id, parse_iso

NAME = "paradiso"
VENUE = "Paradiso"
HOMEPAGE = "https://www.paradiso.nl/"

API = "https://knwxh8dmh1.execute-api.eu-central-1.amazonaws.com/graphql"
TOKEN = "qNG1MfNixLtJU_iE_nvJ3ssmMY5NZ3Nx"  # public token shipped in paradiso.nl's JS bundle
QUERY = """
query ($site: String, $size: Int, $gte: String, $lte: String, $after: [String]) {
  program(site: $site, size: $size, gteStartDateTime: $gte, lteStartDateTime: $lte, searchAfter: $after) {
    events {
      id uri title subtitle startDateTime sort eventStatus soldOut supportAct announceSupport
      location { title }
      image { desktop }
    }
  }
}
"""
PAGE_SIZE = 50
MAX_PAGES = 10


def fetch(client, today: date, days: int = 50) -> list[dict]:
    gte = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    lte = gte + timedelta(days=days)
    variables = {
        "site": "paradisoNederlands",
        "size": PAGE_SIZE,
        "gte": gte.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "lte": lte.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }
    events: list[dict] = []
    for _ in range(MAX_PAGES):
        data = client.post_json(API, {"query": QUERY, "variables": variables},
                                headers={"Authorization": f"Bearer {TOKEN}"})
        if data.get("errors"):
            raise RuntimeError(f"GraphQL error: {data['errors'][0].get('message')}")
        page = data["data"]["program"]["events"] or []
        events.extend(page)
        if len(page) < PAGE_SIZE:
            break
        variables["after"] = page[-1]["sort"]
    return events


STATUS_MAP = {"cancelled": "cancelled", "canceled": "cancelled", "postponed": "moved", "moved": "moved",
              "rescheduled": "moved", "verplaatst": "moved", "afgelast": "cancelled"}


def parse(raw: list[dict], today: date) -> list[Event]:
    out = []
    now = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
    for e in raw:
        title = clean(e["title"])
        support = clean(e.get("supportAct"))
        announce = e.get("announceSupport")
        if support and support.lower() not in title.lower() and (not announce or parse_iso(announce) <= now):
            title = f"{title} + {support}"
        subtitle = clean(e.get("subtitle"))
        locations = [l["title"] for l in (e.get("location") or []) if l.get("title")] if isinstance(e.get("location"), list) \
            else [e["location"]["title"]] if e.get("location") else []
        venue = locations[0] if locations else VENUE
        # subtitles sometimes end with " / Tolhuistuin"; drop that suffix
        if subtitle.endswith("/ " + venue):
            subtitle = subtitle[: -len("/ " + venue)].strip()
        start = parse_iso(e["startDateTime"])
        status = STATUS_MAP.get((e.get("eventStatus") or "").lower(), "normal")
        if status == "normal" and (e.get("soldOut") or "no").lower() in ("yes", "true", "soldout", "sold_out"):
            status = "sold_out"
        default_cat = "club" if start.hour >= 23 or start.hour < 5 else "music"
        images = e.get("image") or []
        out.append(Event(
            id=make_id(NAME, e["id"]),
            title=title,
            subtitle=subtitle or None,
            venue=venue,
            start=start,
            url="https://www.paradiso.nl/" + e["uri"].lstrip("/"),
            category=guess_category(f"{title} {subtitle}", default_cat),
            status=status,
            image=images[0].get("desktop") if images else None,
        ))
    return out
