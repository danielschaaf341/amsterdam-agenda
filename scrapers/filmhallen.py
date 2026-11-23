"""Filmhallen (cinema) – specials and themed programmes (e.g. 'Nineties') only.

Same 'koepel' platform as The Movies: public JSON /fk-feed/agenda.
"""
from __future__ import annotations

from datetime import date

from ._koepel import parse_feed

NAME = "filmhallen"
VENUE = "Filmhallen"
HOMEPAGE = "https://filmhallen.nl/agenda/"
FEED = "https://filmhallen.nl/fk-feed/agenda"


def fetch(client, today: date) -> dict:
    return client.get_json(FEED)


def parse(raw: dict, today: date):
    return parse_feed(raw, NAME, VENUE, HOMEPAGE)
