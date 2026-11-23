"""Joe's Garage (Pretoriusstraat 43 – sociaal centrum). Source: its Radar group agenda (the same agenda its website shows). See _radar.py."""
from __future__ import annotations

from datetime import date

from ._radar import fetch_group, parse_group

NAME = "joesgarage"
VENUE = "Joe's Garage"
HOMEPAGE = "https://joesgarage.nl/"
GROUP = 41  # radar.squat.net group node id


def fetch(client, today: date) -> list[dict]:
    return fetch_group(client, GROUP)


def parse(raw: list[dict], today: date):
    return parse_group(raw, NAME, VENUE)
