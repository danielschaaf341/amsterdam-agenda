"""Westergas – events at the Westergasterrein: festivals, markets, concerts (multi-day → series). Source: agenda HTML cards (see _cards.py)."""
from __future__ import annotations

from datetime import date

from ._cards import fetch_cards, parse_cards

NAME = "westergas"
VENUE = "Westergas"
HOMEPAGE = "https://westergas.nl/agenda/"
SELECTOR = "div.agenda-grid__item"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    from bs4 import BeautifulSoup
    events = parse_cards(raw, today, NAME, VENUE, title_sel="span.event-button__text__title", default_category="other")
    # the byline ends with the hall on the terrain (Pacific Amsterdam, Gashouder, …) → subtitle
    halls = {}
    for card in BeautifulSoup(raw, "html.parser").select("div.agenda-grid__item"):
        t, b = card.select_one(".event-button__text__title"), card.select_one(".event-button__text__byline")
        if t and b:
            lines = [x.strip() for x in b.get_text("\n").split("\n") if x.strip()]
            halls[" ".join(t.get_text().split())] = lines[-1] if lines else ""
    for e in events:
        e.subtitle = halls.get(e.title) or e.subtitle
    return events
