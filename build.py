#!/usr/bin/env python3
"""Assemble the static site in _site/: site/* + data/events.json, data/status.json, venues.json, events.ics."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "site", OUT)
    (OUT / "data").mkdir()
    for name in ("events.json", "status.json"):
        shutil.copy2(ROOT / "data" / name, OUT / "data" / name)
    shutil.copy2(ROOT / "data" / "events.ics", OUT / "events.ics")
    shutil.copy2(ROOT / "venues.json", OUT / "data" / "venues.json")
    (OUT / ".nojekyll").touch()
    print(f"built {OUT}")


if __name__ == "__main__":
    main()
