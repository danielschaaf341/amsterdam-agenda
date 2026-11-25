"""Pllek – NDSM waterfront: film, live music, workshops, dine & DJ. Source: agenda HTML cards (see _cards.py)."""
from __future__ import annotations

from datetime import date

import re

from ._cards import fetch_cards, parse_cards
from .base import collapse_recurring

NAME = "pllek"
VENUE = "Pllek"
HOMEPAGE = "https://pllek.nl/agenda/"
SELECTOR = "ul.fusion-grid > li"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    def cat(title, text):
        t = title.lower()
        if re.search(r"dine|diner|dinner|brunch|lunch", t):
            return "food"
        if re.search(r"ruige rakkers|dj|party|rave", t):
            return "club"
        if re.search(r"film|cinema|screening", t):
            return "film"
        if re.search(r"live|concert|laidback", t):
            return "music"
        return "other"
    # 'Dine & DJ' every Fri/Sat → one weekly food item
    return collapse_recurring(parse_cards(raw, today, NAME, VENUE, category_fn=cat), NAME)
