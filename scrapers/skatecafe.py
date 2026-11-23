"""Skatecafé (Karin & Yvonne), Amsterdam-Noord.

skatecafe.nl serves a bot-check page, but its ticket shop skatecafe.weticket.io links a public
WeTicket RSS feed of upcoming events → see _weticket.py.
"""
from __future__ import annotations

from datetime import date

from ._weticket import feed_url, parse_feed

NAME = "skatecafe"
VENUE = "Skatecafé"
HOMEPAGE = "https://skatecafe.weticket.io/"
FEED = feed_url("569bede7-182b-4831-b426-b741c13d2f37")


def fetch(client, today: date) -> str:
    return client.get_text(FEED)


def parse(raw: str, today: date):
    return parse_feed(raw, NAME, VENUE)
