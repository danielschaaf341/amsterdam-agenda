"""Vrankrijk (Spuistraat 216 – autonoom politiek café). Source: its Radar group agenda (the same agenda its website shows). See _radar.py."""
from __future__ import annotations

from datetime import date

from ._radar import fetch_group, parse_group

NAME = "vrankrijk"
VENUE = "Vrankrijk"
HOMEPAGE = "https://vrankrijk.org/"
GROUP = 137050  # radar.squat.net group node id


def fetch(client, today: date) -> list[dict]:
    return fetch_group(client, GROUP)


def parse(raw: list[dict], today: date):
    return parse_group(raw, NAME, VENUE)
