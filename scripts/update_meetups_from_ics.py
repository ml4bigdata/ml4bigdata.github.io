#!/usr/bin/env python3
import os
from datetime import datetime
from pathlib import Path

import requests
from icalendar import Calendar
import pytz

# --- config ---

ICS_URL_ENV = "OUTLOOK_ICS_URL"
TARGET_FILE = Path("meetups12.md")  # adapt if it's e.g. meetups/index.md
SECTION_HEADER = "## Current & upcoming"
TZ = pytz.timezone("Europe/Helsinki")


def fetch_calendar(url: str) -> Calendar:
    resp = requests.get(url)
    resp.raise_for_status()
    return Calendar.from_ical(resp.content)


def extract_events(cal: Calendar):
    """Return list of (start_dt_aware, summary, location, url) for events."""
    events = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        dtstart = component.get("dtstart")
        if not dtstart:
            continue
        dt = dtstart.dt

        # dt can be date or datetime, with or without tzinfo
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = TZ.localize(dt)
            else:
                dt = dt.astimezone(TZ)
        else:
            # it's a date; interpret as start of day in Helsinki
            dt = TZ.localize(datetime(dt.year, dt.month, dt.day, 0, 0))

        summary = str(component.get("summary", "")).strip()
        location = str(component.get("location", "")).strip()

        # Optional: use Outlook "Online meeting" URL / description URL if present
        url = None
        for field in ("url", "X-ALT-DESC", "description"):
            v = component.get(field)
            if v:
                text = str(v)
                # naive heuristic: grab first http(s) link if any
                for token in text.split():
                    if token.startswith("http://") or token.startswith("https://"):
                        url = token
                        break
            if url:
                break

        events.append((dt, summary, location, url))

    return events


def filter_and_sort_upcoming(events):
    now = datetime.now(TZ)
    upcoming = [e for e in events if e[0] >= now]
    upcoming.sort(key=lambda e: e[0])
    return upcoming


def format_bullet(ev):
    dt, summary, location, url = ev
    # Example: "8 Aug 2025 — Mahsa Asadi: Personalized Mean Estimation · [YouTube](...)"
    date_str = dt.strftime("%-d %b %Y")  # Linux; if this breaks on mac, use "%d %b %Y"

    # Very simple parsing convention:
    # you can encode "Speaker: Title" in the Outlook event title,
    # or just show the raw summary.
    text = summary
    if url:
        return f"* {date_str} — {text} · [Link]({url})"
    else:
        return f"* {date_str} — {text}"


def update_meetups_file(bullets):
    text = TARGET_FILE.read_text(encoding="utf-8")

    before, sep, after = text.partition(SECTION_HEADER)
    if not sep:
        raise RuntimeError(f"Could not find section header '{SECTION_HEADER}' in {TARGET_FILE}")

    # Keep everything after header until the next horizontal rule or blank block.
    # Easiest: split `after` on first '* * *' which you seem to use.
    body, sep2, rest = after.partition("* * *")

    new_section = SECTION_HEADER + "\n" + "\n".join(bullets) + "\n"
    if sep2:
        updated = before + new_section + "* * *" + rest
    else:
        updated = before + new_section

    TARGET_FILE.write_text(updated, encoding="utf-8")


def main():
    ics_url = os.getenv(ICS_URL_ENV)
    if not ics_url:
        raise SystemExit(f"Environment variable {ICS_URL_ENV} not set")

    cal = fetch_calendar(ics_url)
    events = extract_events(cal)
    upcoming = filter_and_sort_upcoming(events)

    bullets = [format_bullet(ev) for ev in upcoming]
    update_meetups_file(bullets)


if __name__ == "__main__":
    main()
