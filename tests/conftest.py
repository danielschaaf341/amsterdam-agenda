import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures"
FIXTURE_DATE = date(2026, 11, 23)  # date the fixtures were recorded


def load_fixture(name: str):
    """Load tests/fixtures/<name>.{json,html,ics} exactly as the scraper's fetch() returned it."""
    for ext in ("json", "html", "ics"):
        p = FIXTURES / f"{name}.{ext}"
        if p.exists():
            text = p.read_text(encoding="utf-8")
            return json.loads(text) if ext == "json" else text
    raise FileNotFoundError(f"no fixture for {name} in {FIXTURES}")


@pytest.fixture
def today():
    return FIXTURE_DATE
