"""Perdu – poetry & literature stage (Kloveniersburgwal). Source: agenda HTML cards (see _cards.py)."""
from __future__ import annotations

from datetime import date

from ._cards import fetch_cards, parse_cards

NAME = "perdu"
VENUE = "Perdu"
HOMEPAGE = "https://perdu.nl/agenda/"
SELECTOR = "div.event"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    return parse_cards(raw, today, NAME, VENUE, default_category="talk")
