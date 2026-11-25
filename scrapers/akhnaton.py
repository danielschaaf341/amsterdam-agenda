"""Akhnaton – world music / club nights, Nieuwezijds Kolk. Source: agenda HTML cards (see _cards.py)."""
from __future__ import annotations

from datetime import date

from ._cards import fetch_cards, parse_cards

NAME = "akhnaton"
VENUE = "Akhnaton"
HOMEPAGE = "https://akhnaton.nl/agenda/"
SELECTOR = "div.e-loop-item"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    return parse_cards(raw, today, NAME, VENUE, title_sel="h2", default_category="music")
