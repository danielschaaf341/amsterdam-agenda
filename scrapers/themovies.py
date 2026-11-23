"""The Movies (cinema) – specials and themed programmes only. Source: public JSON /fk-feed/agenda."""
from __future__ import annotations

from datetime import date

from ._koepel import parse_feed

NAME = "themovies"
VENUE = "The Movies"
HOMEPAGE = "https://themovies.nl/agenda/"
FEED = "https://themovies.nl/fk-feed/agenda"


def fetch(client, today: date) -> dict:
    return client.get_json(FEED)


def parse(raw: dict, today: date):
    return parse_feed(raw, NAME, VENUE, HOMEPAGE)
