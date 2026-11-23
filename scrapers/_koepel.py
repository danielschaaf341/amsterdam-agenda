"""Shared parser for cinemas on the 'koepel' WordPress platform (The Movies, Filmhallen, ...).

Their site loads `/fk-feed/agenda`: {slug: film} with film.tags {key: label} and
film.times[] {program_start 'YYYYMMDDHHMM', program_end, ticket_status, location, tags[]}.

Per the user's wish we skip regular screenings and keep only:
- special screenings (preview, première, +extra, live broadcasts, Q&A, marathon, ...) → kind=event
- themed programmes (e.g. 'Nineties', a director retrospective) → one kind=series per theme
"""
from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import datetime

from .base import Event, clean, local, make_id

# film-level tags that make every screening of that film a special event
# (NB: 'Première' and '+Extra' just label new releases → every screening; not events)
EVENT_FILM_TAGS = {"royal ballet and opera", "national theatre live", "met opera", "voorpremière", "sneak preview",
                   "q&a"}
# show-level tags that make that one screening special
EVENT_SHOW_TAGS = {"preview", "live", "encore", "q&a", "sneak", "premiere", "première", "special",
                   "filmhallen fast forward"}
# generic tags that are neither an event nor a themed programme
IGNORE_TAGS = {"première", "premiere", "+extra", "extra", "verwacht", "laatste kans", "kids", "documentaire", "kunst en cultuur", "klassieker",
               "no subs", "no subtitles", "en subs", "ov", "met pauze", "nl subs", "3d"}
TITLE_SPECIAL = re.compile(r"\b(marathon|double ?bill|sneak|q ?& ?a|quiz|sing[- ]?along|live score|"
                           r"voorpremi[eè]re|preview|special|all[- ]?nighter|filmquiz)\b", re.I)
THEATRE_TAGS = {"royal ballet and opera", "national theatre live", "met opera", "live", "encore"}


def _label(tag: str) -> str:
    return clean(html.unescape(tag))


def _dt(value: str) -> datetime:
    return local(datetime.strptime(value, "%Y%m%d%H%M"))


def parse_feed(feed: dict, source: str, venue: str, homepage: str) -> list[Event]:
    out: list[Event] = []
    themes: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for slug, film in feed.items():
        title = clean(film.get("title")) or slug
        film_tags = [_label(t) for t in (film.get("tags") or {}).values()]
        film_tags_l = {t.lower() for t in film_tags}
        film_event_tags = [t for t in film_tags if t.lower() in EVENT_FILM_TAGS]
        url = film.get("permalink") or homepage
        poster = film.get("poster") or film.get("image") or None
        for show in film.get("times") or []:
            start = _dt(show["program_start"])
            end = _dt(show["program_end"]) if show.get("program_end") else None
            show_tags = [_label(t) for t in (show.get("tags") or []) if isinstance(t, str)]
            special_show = [t for t in show_tags if t.lower() in EVENT_SHOW_TAGS]
            title_hit = TITLE_SPECIAL.search(f"{title} {film.get('subtitle') or ''}")
            for tag in film_tags:
                tl = tag.lower()
                if tl not in IGNORE_TAGS and tl not in EVENT_FILM_TAGS:
                    themes[tag].append((start, title))
            if not (film_event_tags or special_show or title_hit):
                continue  # regular screening: skip
            label = (special_show or film_event_tags or [title_hit.group(0) if title_hit else ""])[0]
            status = "sold_out" if "sold" in (show.get("ticket_status") or "").lower() \
                or "uitverkocht" in (show.get("ticket_status") or "").lower() else "normal"
            is_theatre = film_tags_l & THEATRE_TAGS or {t.lower() for t in special_show} & THEATRE_TAGS
            out.append(Event(
                id=make_id(source, show.get("provider_id") or show.get("child_id") or f"{slug}{start:%Y%m%d%H%M}"),
                title=title if not label or label.lower() in title.lower() else f"{title} ({label})",
                subtitle=" · ".join(x for x in (clean(film.get("subtitle")), show.get("location")) if x) or None,
                venue=venue,
                start=start,
                end=end if end and end > start else None,
                url=url,
                category="theatre" if is_theatre else "film",
                status=status,
                image=poster,
            ))
    for tag, shows in themes.items():
        shows.sort()
        films = sorted({t for _, t in shows})
        if len(films) < 2:
            continue  # one film isn't a themed programme
        out.append(Event(
            id=make_id(source, "series", tag),
            title=f"{tag} bij {venue}",
            subtitle=f"{len(films)} film{'s' if len(films) != 1 else ''}: " + ", ".join(films[:6])
                     + (" …" if len(films) > 6 else ""),
            venue=venue,
            start=shows[0][0],
            end=shows[-1][0],
            url=homepage,
            category="film",
            kind="series",
        ))
    return out
