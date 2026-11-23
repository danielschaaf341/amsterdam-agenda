#!/usr/bin/env python3
"""Run all venue scrapers and write data/events.json, data/status.json and data/events.ics.

Usage:
  python run.py                      # all scrapers
  python run.py --only melkweg zwijger
  python run.py --save-fixtures      # also store each scraper's raw fetch in tests/fixtures/
  python run.py --no-cache           # ignore the on-disk HTTP cache
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import traceback
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

from scrapers import all_scrapers
from scrapers.base import TZ, Event
from scrapers.http import Client
from ics import write_ics

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FIXTURES = ROOT / "tests" / "fixtures"
WINDOW_DAYS = 42  # six weeks

log = logging.getLogger("run")


def norm_title(title: str) -> str:
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", t)[:40]


def in_window(ev: Event, start: datetime, limit: datetime) -> bool:
    last = ev.end or ev.start
    return ev.start < limit and last >= start


def _event_from_dict(d: dict) -> Event:
    return Event(**{**d, "start": datetime.fromisoformat(d["start"]),
                    "end": datetime.fromisoformat(d["end"]) if d.get("end") else None})


def dedupe(events: list[Event]) -> list[Event]:
    by_id: dict[str, Event] = {}
    by_key: dict[tuple, Event] = {}
    for ev in events:
        if ev.id in by_id:
            continue
        key = (ev.venue.casefold(), ev.start.astimezone(TZ).strftime("%Y%m%d%H%M"), norm_title(ev.title))
        if key in by_key:
            continue
        by_id[ev.id] = ev
        by_key[key] = ev
    return list(by_id.values())


def save_fixture(name: str, raw) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    if isinstance(raw, str):
        ext = "ics" if raw.lstrip().startswith("BEGIN:VCALENDAR") else "html"
        (FIXTURES / f"{name}.{ext}").write_text(raw, encoding="utf-8")
    else:
        (FIXTURES / f"{name}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")


def run_scraper(mod, client: Client, today: date, save: bool) -> list[Event]:
    raw = mod.fetch(client, today)
    if save:
        save_fixture(mod.NAME, raw)
    events = []
    for ev in mod.parse(raw, today):
        ev.source = mod.NAME
        try:
            ev.validate()
        except ValueError as exc:
            log.warning("[%s] dropping invalid event: %s", mod.NAME, exc)
            continue
        events.append(ev)
    return events


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="scraper module names to run")
    ap.add_argument("--save-fixtures", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")

    now = datetime.now(TZ)
    today = now.date()
    window_start = datetime.combine(today, datetime.min.time(), tzinfo=TZ)
    window_end = window_start + timedelta(days=WINDOW_DAYS)

    status_path = DATA / "status.json"
    old_status = json.loads(status_path.read_text()).get("venues", {}) if status_path.exists() else {}
    old_events_path = DATA / "events.json"
    old_events = json.loads(old_events_path.read_text())["events"] if old_events_path.exists() else []

    mods = all_scrapers()
    disabled = {m.NAME: m for m in mods if not getattr(m, "ENABLED", True)}
    mods = [m for m in mods if m.NAME not in disabled or (args.only and m.NAME in args.only)]
    if args.only:
        mods = [m for m in mods if m.NAME in args.only]
        if not mods:
            log.error("no scrapers match %s", args.only)
            return 2

    client = Client(use_cache=not args.no_cache)
    all_events: list[Event] = []
    status = dict(old_status) if args.only else {}
    try:
        for mod in mods:
            t0 = time.monotonic()
            entry = {
                "name": mod.VENUE,
                "url": getattr(mod, "HOMEPAGE", ""),
                "last_attempt": now.isoformat(timespec="seconds"),
                "last_success": (old_status.get(mod.NAME) or {}).get("last_success"),
                "events": 0,
                "error": None,
            }
            try:
                events = run_scraper(mod, client, today, args.save_fixtures)
                upcoming = [e for e in events if in_window(e, window_start, window_end)]
                if not events:
                    raise RuntimeError("scraper returned 0 events (site changed?)")
                all_events.extend(upcoming)
                entry.update(events=len(upcoming), last_success=now.isoformat(timespec="seconds"))
                log.info("[%s] %d events (%d in window) in %.1fs", mod.NAME, len(events), len(upcoming),
                         time.monotonic() - t0)
            except Exception as exc:  # one scraper must never break the run
                entry["error"] = f"{type(exc).__name__}: {exc}"[:300]
                log.error("[%s] FAILED: %s", mod.NAME, entry["error"])
                log.debug(traceback.format_exc())
                # keep last run's events of this source (still in window) so a hiccup doesn't empty a venue
                kept = [e for e in (_event_from_dict(d) for d in old_events if d.get("source") == mod.NAME)
                        if in_window(e, window_start, window_end)]
                all_events.extend(kept)
                entry["events"] = len(kept)
                entry["stale"] = bool(kept)
                if kept:
                    log.info("[%s] kept %d events from the previous run", mod.NAME, len(kept))
            status[mod.NAME] = entry
    finally:
        client.close()

    for name, mod in disabled.items():
        if not (args.only and name in args.only):
            status[name] = {"name": mod.VENUE, "url": getattr(mod, "HOMEPAGE", ""), "disabled": True,
                            "reason": getattr(mod, "DISABLED_REASON", ""), "events": 0, "error": None,
                            "last_success": (old_status.get(name) or {}).get("last_success")}

    if args.only:
        # keep events of scrapers we didn't run, so a partial run doesn't wipe the site
        ran = {m.NAME for m in mods}
        for d in old_events:
            if d.get("source") not in ran:
                ev = _event_from_dict(d)
                if in_window(ev, window_start, window_end):
                    all_events.append(ev)

    events = sorted(dedupe(all_events), key=lambda e: (e.start, e.venue, e.title))
    DATA.mkdir(exist_ok=True)
    generated = now.isoformat(timespec="seconds")
    (DATA / "events.json").write_text(json.dumps(
        {"generated": generated, "window_days": WINDOW_DAYS, "count": len(events),
         "events": [e.to_dict() for e in events]}, ensure_ascii=False, indent=1), encoding="utf-8")
    status_path.write_text(json.dumps({"generated": generated, "venues": status}, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    write_ics(events, DATA / "events.ics", generated=now)

    failed = [n for n, s in status.items() if s.get("error")]
    active = [n for n, s in status.items() if not s.get("disabled")]
    log.info("wrote %d events; %d/%d scrapers ok; %d HTTP requests%s", len(events), len(active) - len(failed),
             len(active), client.requests_made, f"; FAILED: {', '.join(failed)}" if failed else "")
    return 1 if failed and len(failed) == len(active) else 0


if __name__ == "__main__":
    sys.exit(main())
