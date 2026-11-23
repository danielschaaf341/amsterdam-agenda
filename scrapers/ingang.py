"""Ingang (Gedempt Hamerkanaal 86, Noord). Source: WeTicket RSS feed of ingang.weticket.io."""
from __future__ import annotations

from datetime import date

from ._weticket import feed_url, parse_feed

NAME = "ingang"
VENUE = "Ingang"
HOMEPAGE = "https://ingang.weticket.io/"
FEED = feed_url("01a0241b-8ad7-7097-b411-80deb23082f9")


def fetch(client, today: date) -> str:
    return client.get_text(FEED)


def parse(raw: str, today: date):
    return parse_feed(raw, NAME, VENUE)
