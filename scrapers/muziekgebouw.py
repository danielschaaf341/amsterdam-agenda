"""Muziekgebouw aan 't IJ – Peppered CMS behind a BunnyCDN JS check → rendered with Playwright. See _peppered.py."""
from __future__ import annotations

from datetime import date

from ._peppered import fetch_pages, parse_pages

NAME = "muziekgebouw"
VENUE = "Muziekgebouw aan 't IJ"
HOMEPAGE = "https://www.muziekgebouw.nl/nl/agenda"
BASE = "https://www.muziekgebouw.nl"


def fetch(client, today: date) -> list[str]:
    return fetch_pages(client, HOMEPAGE)


def parse(raw: list[str], today: date):
    events = parse_pages(raw, today, NAME, VENUE, BASE, location_key="muziekgebouw", trust_class=False)
    for e in events:
        if e.category == "theatre" and "music" == "music":
            e.category = "music"  # concert hall: genre labels like 'jazz'/'wereld' still mean music
    return events
