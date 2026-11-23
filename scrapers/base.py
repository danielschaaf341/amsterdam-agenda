"""Shared schema and helpers for all venue scrapers.

Every scraper module returns a list of `Event` objects. See CLAUDE.md for the contract.
"""
from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Amsterdam")

CATEGORIES = ("film", "music", "club", "talk", "theatre", "jazz", "other")
STATUSES = ("normal", "sold_out", "cancelled", "moved")
KINDS = ("event", "series")  # series = a themed period (retrospective, festival) running start..end


@dataclass
class Event:
    id: str
    title: str
    venue: str
    start: datetime
    url: str
    category: str = "other"
    end: datetime | None = None
    status: str = "normal"
    price: str | None = None
    image: str | None = None
    kind: str = "event"
    all_day: bool = False  # True when only the date is known (start is then 00:00 local)
    subtitle: str | None = None
    source: str = ""  # scraper module name, filled in by run.py

    def validate(self) -> None:
        if not self.id or not self.title or not self.venue or not self.url:
            raise ValueError(f"missing required field in {self!r}")
        if self.category not in CATEGORIES:
            raise ValueError(f"bad category {self.category!r} for {self.title!r}")
        if self.status not in STATUSES:
            raise ValueError(f"bad status {self.status!r} for {self.title!r}")
        if self.kind not in KINDS:
            raise ValueError(f"bad kind {self.kind!r} for {self.title!r}")
        if self.start.tzinfo is None:
            raise ValueError(f"naive start datetime for {self.title!r}")
        if self.end is not None and self.end < self.start:
            raise ValueError(f"end before start for {self.title!r}")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.astimezone(TZ).isoformat()
        d["end"] = self.end.astimezone(TZ).isoformat() if self.end else None
        if not self.all_day:
            d.pop("all_day")
        return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------- text helpers

def clean(text: str | None) -> str:
    """Unescape HTML entities, strip tags and collapse whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def make_id(source: str, *parts) -> str:
    """Stable id: '<source>-<native id>' or a short hash of the given parts."""
    if len(parts) == 1 and re.fullmatch(r"[\w.-]{1,40}", str(parts[0])):
        return f"{source}-{parts[0]}"
    h = hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]
    return f"{source}-{h}"


# ---------------------------------------------------------------- time helpers

def local(dt: datetime) -> datetime:
    """Attach Europe/Amsterdam to a naive local datetime; convert aware ones."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def parse_iso(value: str, assume_local: bool = False) -> datetime:
    """Parse ISO 8601 ('Z', offsets, microseconds). assume_local=True ignores a (wrong) offset."""
    v = value.strip().replace("Z", "+00:00")
    v = re.sub(r"\.\d+", "", v)
    dt = datetime.fromisoformat(v)
    if assume_local:
        return dt.replace(tzinfo=TZ)
    return local(dt)


MONTHS_NL = {
    "jan": 1, "januari": 1, "feb": 2, "februari": 2, "mrt": 3, "maart": 3, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "mei": 5, "may": 5, "jun": 6, "juni": 6, "june": 6, "jul": 7, "juli": 7,
    "july": 7, "aug": 8, "augustus": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10, "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12, "january": 1, "february": 2,
}


def month_number(name: str) -> int:
    key = name.lower().strip(". ")
    if key in MONTHS_NL:
        return MONTHS_NL[key]
    if key[:3] in MONTHS_NL:
        return MONTHS_NL[key[:3]]
    raise ValueError(f"unknown month {name!r}")


def infer_year(day: int, month: int, today: date, max_past_days: int = 60) -> date:
    """For yearless dates: pick the year that puts the date nearest after `today`.

    Dates up to `max_past_days` in the past stay in the current year (running events).
    """
    candidate = date(today.year, month, day)
    if candidate < today - timedelta(days=max_past_days):
        candidate = date(today.year + 1, month, day)
    return candidate


def parse_hhmm(text: str) -> time:
    m = re.search(r"(\d{1,2})[:.](\d{2})", text)
    if not m:
        raise ValueError(f"no time in {text!r}")
    return time(int(m.group(1)) % 24, int(m.group(2)))


# ---------------------------------------------------------------- runs

def is_run(starts: list[datetime], threshold: int = 4, max_median_gap_days: int = 3) -> bool:
    """True for a theatre/film *run*: more than `threshold` performances close together.

    Such productions are emitted as one kind=series instead of flooding the daily list. A monthly
    recurring show (median gap > 3 days) is not a run and stays individual events.
    """
    starts = sorted(starts)
    if len(starts) <= threshold:
        return False
    gaps = sorted((b - a).days for a, b in zip(starts, starts[1:]))
    return gaps[len(gaps) // 2] <= max_median_gap_days


def run_span(starts: list[datetime], max_gap_days: int = 30) -> tuple[datetime, datetime]:
    """First..last performance of the main run, ignoring stray dates after a long gap (festival reprise)."""
    starts = sorted(starts)
    end = starts[0]
    for a, b in zip(starts, starts[1:]):
        if (b - a).days > max_gap_days:
            break
        end = b
    return starts[0], end


# ---------------------------------------------------------------- iCalendar helper

def parse_ics(text: str) -> list[dict]:
    """Minimal iCalendar reader: returns one dict per VEVENT.

    Keys are property names (params dropped); DTSTART/DTEND become aware datetimes
    (UTC 'Z', TZID=..., or floating = Amsterdam). Text values are unescaped.
    """
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events, cur = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, value = line.split(":", 1)
            name, *params = head.split(";")
            params = dict(p.split("=", 1) for p in params if "=" in p)
            if name in ("DTSTART", "DTEND"):
                if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
                    dt = datetime.strptime(value[:8], "%Y%m%d")
                    cur[name + "_IS_DATE"] = True  # all-day (no time given)
                else:
                    dt = datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")
                if value.endswith("Z"):
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                elif "TZID" in params:
                    dt = dt.replace(tzinfo=ZoneInfo(params["TZID"]))
                cur[name] = local(dt)
            else:
                cur[name] = value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
    return events


# ---------------------------------------------------------------- category helper

_CATEGORY_KEYWORDS = [
    ("talk", r"\b(book ?club|leesclub|boekenclub)\b"),  # before "club"
    ("jazz", r"\bjazz"),
    ("club", r"\b(club|clubnacht|clubnight|dj|djs|techno|house|rave|party|feest|disco|all ?nighter)\b"),
    ("talk", r"\b(talk|lezing|debat|gesprek|in conversation|lecture|panel|podcast|boekpresentatie|interview)\b"),
    ("film", r"\b(film|films|screening|cinema|vertoning|documentaire)\b"),
    ("theatre", r"\b(theater\w*|theatre|toneel\w*|voorstelling|dans|dansvoorstelling|dance performance|cabaret|comedy|opera)\b"),
]


def guess_category(text: str, default: str = "other") -> str:
    t = (text or "").lower()
    for cat, pattern in _CATEGORY_KEYWORDS:
        if re.search(pattern, t):
            return cat
    return default
