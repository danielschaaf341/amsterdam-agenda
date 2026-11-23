"""Amsterdam Alternative network – all affiliated (sub)cultural venues in one go.

Source: the same JSON service ot301.nl uses, without a venue filter:
  https://amsterdamalternative.nl/services/get-events-past-v25.php?month=M&months=1
One call per month (current + next). The server is slow (~1–2 min per month) – that's fine weekly.
Covers e.g. Cinetol, Plein Theater, Teatro Munganga, Splendor, ADM Noord, Nieuwland, Badhuistheater,
Pakhuis Wilhelmina, Vondelbunker, Plantage Dok, LIMA, …
Venues with their own scraper are skipped (OT301, OCCII, Filmhuis Cavia, De Nieuwe Anita), as are
venues outside Amsterdam. Bar entries are dropped; food → "food"; repeating items → kind="weekly".
"""
from __future__ import annotations

from datetime import date

from .base import collapse_recurring
from .ot301 import API, parse_items

NAME = "amsterdamalternative"
VENUE = "Amsterdam Alternative (netwerk)"
HOMEPAGE = "https://amsterdamalternative.nl/agenda"
MONTHS = 2
OWN_SCRAPER_VENUES = {"ot301", "occii", "filmhuis cavia", "de nieuwe anita",
                      "pakhuis wilhelmina"}  # = Mezrab's building; mezrab.py has the full agenda
VENUE_NAMES = {"admnoord - ‘t groene veld": "ADM Noord – 't Groene Veld", "badhuistheater": "Mike's Badhuistheater",
               "pos (possibilities open studio)": "POS (possibilities open studio)",
               "[ woonruimte coöperatief ]": "Woonruimte Coöperatief", "wg": "WG-terrein"}


def fetch(client, today: date) -> list[dict]:
    items = []
    for i in range(MONTHS):
        month = (today.month - 1 + i) % 12 + 1
        data = client.get_json(API, params={"month": month, "months": 1}, timeout=240)
        items.extend(data.get("items") or [])
    return items


def parse(raw: list[dict], today: date):
    keep = []
    for x in raw:
        name = (x.get("venue") or "").strip()
        low = name.lower()
        if low in OWN_SCRAPER_VENUES or "zaandam" in low or not name:
            continue
        keep.append({**x, "venue": VENUE_NAMES.get(low, name)})
    return collapse_recurring(parse_items(keep, None, NAME), NAME)
