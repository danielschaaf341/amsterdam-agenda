"""Mediamatic (art, biotech, food; Dijksgracht). Source: events list HTML (see _cards.py).

Items: 'Performance: | Mediamatic Biotoop | <title> | 27 | Nov 2026 | 10 | Dec 2026' → ranges become series.
"""
from __future__ import annotations

import re
from datetime import date

from ._cards import fetch_cards, parse_cards

NAME = "mediamatic"
VENUE = "Mediamatic"
HOMEPAGE = "https://www.mediamatic.net/en/events"
SELECTOR = "li.list__item"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    def cat(title, text):
        kind = text.split("|", 1)[0].lower()
        if re.search(r"dinner|diner|maal|food|lunch", f"{title} {kind}", re.I):
            return "food"
        if re.search(r"lecture|talk|presentation|conference|symposium", kind):
            return "talk"
        if re.search(r"performance|theat", kind):
            return "theatre"
        if re.search(r"film|screening", kind):
            return "film"
        return "other"
    # skip the permanent 'Open Daily Tours'
    return parse_cards(raw, today, NAME, VENUE, title_sel="h3", category_fn=cat,
                       skip=lambda title, text: "daily tours" in text.lower())
