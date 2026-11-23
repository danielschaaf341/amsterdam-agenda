"""Theater Bellevue – Peppered CMS behind a BunnyCDN JS check → rendered with Playwright. See _peppered.py."""
from __future__ import annotations

from datetime import date

from ._peppered import fetch_pages, parse_pages

NAME = "bellevue"
VENUE = "Theater Bellevue"
HOMEPAGE = "https://www.theaterbellevue.nl/agenda"
BASE = "https://www.theaterbellevue.nl"


def fetch(client, today: date) -> list[str]:
    return fetch_pages(client, HOMEPAGE)


def parse(raw: list[str], today: date):
    return parse_pages(raw, today, NAME, VENUE, BASE, location_key="bellevue", trust_class=True)
