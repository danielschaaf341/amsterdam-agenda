"""Nachbar (club, Nieuwezijds Voorburgwal 169). Source: Stager shop JSON-LD (see _stager.py)."""
from __future__ import annotations

from datetime import date

from ._stager import fetch_shop, parse_shop

NAME = "nachbar"
VENUE = "Nachbar"
HOMEPAGE = "https://nachbar.stager.co/shop/nachbar"


def fetch(client, today: date) -> list[dict]:
    return fetch_shop(client, HOMEPAGE)


def parse(raw: list[dict], today: date):
    return parse_shop(raw, NAME, VENUE)
