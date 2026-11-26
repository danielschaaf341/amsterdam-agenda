"""Map view: every venue name the scrapers produce has coordinates in venues.json (or is listed on
purpose under not_on_map), and every coordinate lies in Amsterdam (incl. Weesp, Zuidoost, Noord)."""
import json

import pytest

from conftest import FIXTURE_DATE, ROOT, load_fixture
from scrapers import all_scrapers

VENUES = json.loads((ROOT / "venues.json").read_text(encoding="utf-8"))
BBOX = (52.27, 52.45, 4.72, 5.10)   # lat min/max, lng min/max: Amsterdam municipality incl. Weesp
KNOWN = {k.lower() for part in ("venues", "aliases", "not_on_map") for k in VENUES.get(part, {})}


def test_coordinates_inside_amsterdam():
    for name, v in VENUES["venues"].items():
        assert BBOX[0] <= v["lat"] <= BBOX[1] and BBOX[2] <= v["lng"] <= BBOX[3], f"{name} lies outside Amsterdam"
        assert v.get("address"), f"{name} has no address"


def test_aliases_point_to_venues():
    for alias, target in VENUES.get("aliases", {}).items():
        assert target in VENUES["venues"], f"alias {alias} → unknown venue {target}"


def test_not_on_map_has_reason():
    for name, why in VENUES["not_on_map"].items():
        assert why and name not in VENUES["venues"], name


@pytest.mark.parametrize("mod", all_scrapers(), ids=lambda m: m.NAME)
def test_fixture_venues_are_on_the_map(mod):
    try:
        raw = load_fixture(mod.NAME)
    except FileNotFoundError:
        pytest.skip("no fixture")
    missing = sorted({e.venue for e in mod.parse(raw, FIXTURE_DATE)})
    missing = [v for v in missing if v.lower() not in KNOWN]
    assert not missing, f"add to venues.json (venues or not_on_map): {missing}"
