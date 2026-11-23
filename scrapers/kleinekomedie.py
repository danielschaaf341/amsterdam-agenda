"""De Kleine Komedie – Peppered CMS behind a BunnyCDN JS check → rendered with Playwright. See _peppered.py."""
from __future__ import annotations

from datetime import date

from ._peppered import fetch_pages, parse_pages

NAME = "kleinekomedie"
VENUE = "De Kleine Komedie"
HOMEPAGE = "https://www.dekleinekomedie.nl/agenda"
BASE = "https://www.dekleinekomedie.nl"


def fetch(client, today: date) -> list[str]:
    return fetch_pages(client, HOMEPAGE)


def parse(raw: list[str], today: date):
    return parse_pages(raw, today, NAME, VENUE, BASE, location_key="kleine komedie", trust_class=False)
