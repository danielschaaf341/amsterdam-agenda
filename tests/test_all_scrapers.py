"""Contract tests every scraper must pass against its saved fixture."""
import pytest

from conftest import FIXTURE_DATE, load_fixture
from scrapers import all_scrapers
from scrapers.base import CATEGORIES

SCRAPERS = all_scrapers()


@pytest.mark.parametrize("mod", SCRAPERS, ids=lambda m: m.NAME)
def test_module_contract(mod):
    for attr in ("NAME", "VENUE", "HOMEPAGE", "fetch", "parse"):
        assert hasattr(mod, attr), f"{mod.__name__} misses {attr}"
    assert mod.__name__.endswith("." + mod.NAME)


@pytest.mark.parametrize("mod", SCRAPERS, ids=lambda m: m.NAME)
def test_parses_fixture(mod):
    try:
        raw = load_fixture(mod.NAME)
    except FileNotFoundError:
        if not getattr(mod, "ENABLED", True):
            pytest.skip(f"{mod.NAME} is disabled and has no full fixture")
        raise
    events = mod.parse(raw, FIXTURE_DATE)
    assert len(events) >= 1, "fixture should yield events"
    ids = [e.id for e in events]
    assert len(ids) == len(set(ids)), "ids must be unique"
    for e in events:
        e.validate()
        assert e.id.startswith(mod.NAME + "-")
        assert e.category in CATEGORIES
        assert e.url.startswith("http")
        assert str(e.start.tzinfo) == "Europe/Amsterdam"
        assert e.title == e.title.strip() and "  " not in e.title and "&amp;" not in e.title
