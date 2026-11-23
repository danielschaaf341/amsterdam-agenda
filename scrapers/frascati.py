"""Frascati – Peppered CMS behind a BunnyCDN JS check → rendered with Playwright. See _peppered.py."""
from __future__ import annotations

from datetime import date

from ._peppered import fetch_pages, parse_pages

NAME = "frascati"
VENUE = "Frascati"
HOMEPAGE = "https://www.frascatitheater.nl/nl/agenda"
BASE = "https://www.frascatitheater.nl"


def fetch(client, today: date) -> list[str]:
    return fetch_pages(client, HOMEPAGE)


def parse(raw: list[str], today: date):
    return parse_pages(raw, today, NAME, VENUE, BASE, location_key="frascati", trust_class=True)
