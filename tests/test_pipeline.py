"""Tests for run.py: dedupe, window, isolation of failing scrapers, ics output."""
import json
import types
from datetime import datetime, timedelta

import run
from ics import to_ics
from scrapers.base import TZ, Event


def ev(id, title="X", venue="V", day=1, hour=20, **kw):
    return Event(id=id, title=title, venue=venue, start=datetime(2026, 12, day, hour, tzinfo=TZ),
                 url="https://example.org", **kw)


def test_dedupe_by_id_and_key():
    a = ev("a-1", "Some Band")
    b = ev("a-1", "Some Band (dup id)")
    c = ev("b-9", "SOME BAND!", day=1)  # same venue+time+normalized title from another source
    d = ev("b-10", "Other", day=2)
    assert [e.id for e in run.dedupe([a, b, c, d])] == ["a-1", "b-10"]


def test_window_keeps_running_series():
    start = datetime(2026, 11, 23, tzinfo=TZ)
    limit = start + timedelta(days=42)
    series = Event(id="s-1", title="Retro", venue="V", url="https://x", kind="series",
                   start=datetime(2026, 10, 1, tzinfo=TZ), end=datetime(2026, 12, 31, tzinfo=TZ))
    old = ev("o-1", day=1)
    old.start = datetime(2026, 11, 1, 20, tzinfo=TZ)
    far = ev("f-1")
    far.start = datetime(2027, 3, 1, 20, tzinfo=TZ)
    assert run.in_window(series, start, limit)
    assert not run.in_window(old, start, limit)
    assert not run.in_window(far, start, limit)


def test_failing_scraper_does_not_break_run(tmp_path, monkeypatch):
    good = types.SimpleNamespace(NAME="good", VENUE="Good", HOMEPAGE="https://good",
                                 fetch=lambda c, t: None,
                                 parse=lambda raw, t: [Event(id="good-1", title="Fine", venue="Good",
                                                             start=datetime.now(TZ) + timedelta(days=1),
                                                             url="https://good")])

    def boom(c, t):
        raise ConnectionError("site down")

    bad = types.SimpleNamespace(NAME="bad", VENUE="Bad", HOMEPAGE="https://bad", fetch=boom, parse=None)
    monkeypatch.setattr(run, "all_scrapers", lambda: [bad, good])
    monkeypatch.setattr(run, "DATA", tmp_path)
    assert run.main([]) == 0
    events = json.loads((tmp_path / "events.json").read_text())["events"]
    status = json.loads((tmp_path / "status.json").read_text())["venues"]
    assert [e["id"] for e in events] == ["good-1"]
    assert status["bad"]["error"].startswith("ConnectionError")
    assert status["good"]["error"] is None and status["good"]["events"] == 1
    assert (tmp_path / "events.ics").read_text().count("BEGIN:VEVENT") == 1


def test_ics_format():
    e = ev("x-1", "Komma, puntkomma; en een heel lange titel " * 3, status="sold_out")
    text = to_ics([e], datetime(2026, 11, 23, tzinfo=TZ))
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n")
    assert "DTSTART:20261201T190000Z" in text  # 20:00 Amsterdam = 19:00 UTC
    assert "[UITVERKOCHT]" in text and "\\," in text and "\\;" in text
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))


def test_failed_scraper_keeps_previous_events(tmp_path, monkeypatch):
    soon = datetime.now(TZ) + timedelta(days=2)
    ok = types.SimpleNamespace(NAME="flaky", VENUE="Flaky", HOMEPAGE="https://flaky", fetch=lambda c, t: None,
                               parse=lambda raw, t: [Event(id="flaky-1", title="Kept", venue="Flaky",
                                                           start=soon, url="https://flaky")])
    monkeypatch.setattr(run, "DATA", tmp_path)
    monkeypatch.setattr(run, "all_scrapers", lambda: [ok])
    assert run.main([]) == 0  # first run succeeds

    def boom(c, t):
        raise ConnectionError("empty response")

    monkeypatch.setattr(run, "all_scrapers", lambda: [types.SimpleNamespace(**{**vars(ok), "fetch": boom})])
    run.main([])
    events = json.loads((tmp_path / "events.json").read_text())["events"]
    status = json.loads((tmp_path / "status.json").read_text())["venues"]["flaky"]
    assert [e["id"] for e in events] == ["flaky-1"]
    assert status["error"] and status["stale"] and status["last_success"]
