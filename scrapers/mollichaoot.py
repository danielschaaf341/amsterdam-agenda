"""Molli Chaoot (Van Ostadestraat 55hs – vegan voku). Source: its Radar group agenda. See _radar.py."""
from __future__ import annotations

from datetime import date

from ._radar import fetch_group, parse_group

NAME = "mollichaoot"
VENUE = "Molli Chaoot"
HOMEPAGE = "https://radar.squat.net/en/molli-chaoot"
GROUP = 567796  # radar.squat.net group node id


def fetch(client, today: date) -> list[dict]:
    return fetch_group(client, GROUP)


def parse(raw: list[dict], today: date):
    return parse_group(raw, NAME, VENUE)
