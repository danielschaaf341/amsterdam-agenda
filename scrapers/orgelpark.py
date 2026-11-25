"""Orgelpark – experimental organ & new music. Source: agenda HTML cards (see _cards.py)."""
from __future__ import annotations

from datetime import date

from ._cards import fetch_cards, parse_cards

NAME = "orgelpark"
VENUE = "Orgelpark"
HOMEPAGE = "https://www.orgelpark.nl/agenda"
SELECTOR = "article.listitem"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    return parse_cards(raw, today, NAME, VENUE, title_sel="h2.listitem-title", default_category="music",
                       category_fn=lambda title, text: "music")  # 'concert met gratis lunch' is still music
