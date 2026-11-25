"""Boom Chicago – comedy & improv (dates only, no times). Source: agenda HTML cards (see _cards.py)."""
from __future__ import annotations

from datetime import date

from ._cards import fetch_cards, parse_cards

NAME = "boomchicago"
VENUE = "Boom Chicago"
HOMEPAGE = "https://boomchicago.nl/shows/"
SELECTOR = "div.js-grid-activity"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    return parse_cards(raw, today, NAME, VENUE, title_sel="h4.activity__title", default_category="theatre",
                       category_fn=lambda title, text: "theatre")  # regular nightly shows have no date → skipped
