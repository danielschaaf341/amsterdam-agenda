"""RADION (club, Louwesweg 1). Source: its Stager shop JSON-LD (radionamsterdam.stager.co)."""
from __future__ import annotations

from datetime import date

from ._stager import fetch_shop, parse_shop

NAME = "radion"
VENUE = "Radion"
HOMEPAGE = "https://radionamsterdam.stager.co/shop/default"


def fetch(client, today: date) -> list[dict]:
    return fetch_shop(client, HOMEPAGE)


def parse(raw: list[dict], today: date):
    return parse_shop(raw, NAME, VENUE)
