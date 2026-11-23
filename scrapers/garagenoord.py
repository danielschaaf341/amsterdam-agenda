"""Garage Noord (club). Source: WeTicket RSS feed of garagenoord.weticket.io (exact times).

garagenoord.com/club lists the same nights but with dates only; the feed has start/end times.
"""
from __future__ import annotations

from datetime import date

from ._weticket import feed_url, parse_feed

NAME = "garagenoord"
VENUE = "Garage Noord"
HOMEPAGE = "https://www.garagenoord.com/club"
FEED = feed_url("66e9ee18-9ff4-49b2-8c2b-a082710dd5e2")


def fetch(client, today: date) -> str:
    return client.get_text(FEED)


def parse(raw: str, today: date):
    events = parse_feed(raw, NAME, VENUE)
    for e in events:
        if e.category == "music" and e.start.hour >= 21:
            e.category = "club"  # it's a club: late music nights are club nights
    return events
