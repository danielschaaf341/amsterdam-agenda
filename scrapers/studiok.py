"""Studio/K – student-run cinema/café; its 'Events in /K' page lists specials (Q&A, screenings with intro, parties). Source: agenda HTML cards (see _cards.py)."""
from __future__ import annotations

from datetime import date

from ._cards import fetch_cards, parse_cards

NAME = "studiok"
VENUE = "Studio/K"
HOMEPAGE = "https://studio-k.nu/events/"
SELECTOR = "div.events-lijst li"


def fetch(client, today: date) -> str:
    return fetch_cards(client, HOMEPAGE, SELECTOR)


def parse(raw: str, today: date):
    return parse_cards(raw, today, NAME, VENUE, title_sel="span.title", default_category="film")
