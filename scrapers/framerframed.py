"""Framer Framed – art & activism: talks, book launches, exhibitions (date ranges → series). Source: agenda HTML cards (see _cards.py)."""
from __future__ import annotations

import re
from datetime import date

from ._cards import fetch_cards, parse_cards

NAME = "framerframed"
VENUE = "Framer Framed"
HOMEPAGE = "https://framerframed.nl/agenda/"
SELECTOR = "a.events-event--future"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    def cat(title, text):
        if re.match(r"(tentoonstelling|exhibition|presentatie|framer framed noord:)", title, re.I):
            return "other"
        if re.search(r"film|screening", title, re.I):
            return "film"
        return "talk"
    return parse_cards(raw, today, NAME, VENUE, category_fn=cat)
