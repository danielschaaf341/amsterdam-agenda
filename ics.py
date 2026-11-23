"""Write an iCalendar (RFC 5545) feed of all events. No dependencies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from scrapers.base import Event

DEFAULT_DURATION = timedelta(hours=2)
STATUS_PREFIX = {"sold_out": "[UITVERKOCHT] ", "cancelled": "[AFGELAST] ", "moved": "[VERPLAATST] "}


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Fold lines longer than 75 octets (RFC 5545 §3.1)."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > 74:
            out.append(cur.decode())
            cur = b" " + b
        else:
            cur += b
    out.append(cur.decode())
    return "\r\n".join(out)


def _utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_ics(events: list[Event], generated: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//amsterdam-agenda//NL", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", "X-WR-CALNAME:Amsterdam agenda", "X-WR-TIMEZONE:Europe/Amsterdam",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D",
    ]
    stamp = _utc(generated)
    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{ev.id}@amsterdam-agenda")
        lines.append(f"DTSTAMP:{stamp}")
        if ev.kind == "series" or ev.all_day:
            # all-day range for themed periods
            end_day = (ev.end or ev.start).date() + timedelta(days=1)
            lines.append(f"DTSTART;VALUE=DATE:{ev.start.strftime('%Y%m%d')}")
            lines.append(f"DTEND;VALUE=DATE:{end_day.strftime('%Y%m%d')}")
        else:
            lines.append(f"DTSTART:{_utc(ev.start)}")
            end = ev.end if ev.end and ev.end - ev.start < timedelta(hours=24) else ev.start + DEFAULT_DURATION
            lines.append(f"DTEND:{_utc(end)}")
        lines.append("SUMMARY:" + _esc(STATUS_PREFIX.get(ev.status, "") + ev.title))
        lines.append("LOCATION:" + _esc(ev.venue))
        desc = " · ".join(x for x in (ev.subtitle, ev.category, ev.price) if x)
        if desc:
            lines.append("DESCRIPTION:" + _esc(desc + "\n" + ev.url))
        lines.append("URL:" + ev.url)
        lines.append("CATEGORIES:" + _esc(ev.category))
        if ev.status == "cancelled":
            lines.append("STATUS:CANCELLED")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"


def write_ics(events: list[Event], path: Path, generated: datetime) -> None:
    path.write_text(to_ics(events, generated), encoding="utf-8", newline="")
