#!/usr/bin/env python3
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import requests
from icalendar import Calendar
import pytz

# --- config ---

ICS_URL_ENV = "OUTLOOK_ICS_URL"
TARGET_FILE = Path("meetups12.md")  # adapt if it's e.g. meetups/index.md
SECTION_HEADER = "## Current & upcoming"  # anchor text in your markdown
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

        # --- URL detection ---

        url = None

        # 1) Check if LOCATION is a YouTube or Zoom URL
        if location:
            loc_lower = location.lower()
            if (
                "youtu.be" in loc_lower
                or "youtube.com" in loc_lower
                or "zoom.us" in loc_lower
                or "zoom.com" in loc_lower
                or "aalto.zoom" in loc_lower
            ):
                url = location.strip()

        # 2) If no URL yet, search in URL / X-ALT-DESC / DESCRIPTION fields
        if not url:
            for field in ("url", "X-ALT-DESC", "description"):
                v = component.get(field)
                if v:
                    text = str(v)
                    for token in text.split():
                        token = token.strip()
                        if token.startswith("http://") or token.startswith("https://"):
                            url = token
                            break
                if url:
                    break

        events.append((dt, summary, location, url))

    return events


def split_upcoming_past(events):
    """Split into upcoming (dt >= now) and past (dt < now)."""
    now = datetime.now(TZ)
    upcoming = []
    past = []
    for ev in events:
        if ev[0] >= now:
            upcoming.append(ev)
        else:
            past.append(ev)

    # Upcoming: chronological (soonest first)
    upcoming.sort(key=lambda e: e[0])
    # Past: reverse chronological (latest first)
    past.sort(key=lambda e: e[0], reverse=True)

    return upcoming, past


def format_link_label(url: str) -> str:
    """Choose a nice label based on the URL."""
    u = url.lower()
    if "zoom" in u:
        return "💻 Zoom"
    if "youtu" in u or "youtube" in u:
        return "🎥 Recording"
    if "slides" in u or u.endswith(".pdf") or u.endswith(".pptx") or u.endswith(".ppt"):
        return "📝 Slides"
    return "🔗 Link"


def format_bullet(ev):
    dt, summary, location, url = ev
    # Example: "8 Aug 2025 — Title (Location) · [🎥 Recording](...)"
    # On some systems, "%-d" may not work; use "%d" if needed
    try:
        date_str = dt.strftime("%-d %b %Y")
    except ValueError:
        date_str = dt.strftime("%d %b %Y")

    text = summary or "(No title)"

    # Avoid printing the location if it's exactly the URL (e.g. YouTube/Zoom in location)
    if location and (not url or location.strip() != url.strip()):
        text += f" ({location})"

    if url:
        label = format_link_label(url)
        return f"* {date_str} — {text} · [{label}]({url})"
    else:
        return f"* {date_str} — {text}"


def render_section_markdown(upcoming, past) -> str:
    """Build the entire markdown block that will replace the section."""
    parts = []

    # Keep the original header text as anchor
    parts.append(SECTION_HEADER)
    parts.append("")

    # --- Upcoming ---
    parts.append("### Upcoming")
    if upcoming:
        for ev in upcoming:
            parts.append(format_bullet(ev))
    else:
        parts.append("_No upcoming meetups scheduled. Stay tuned!_")
    parts.append("")

    # --- Past events, grouped by year ---
    parts.append("### Past events")
    if past:
        events_by_year = defaultdict(list)
        for ev in past:
            year = ev[0].year
            events_by_year[year].append(ev)

        # Show most recent years first
        for year in sorted(events_by_year.keys(), reverse=True):
            parts.append(f"#### {year}")
            # within each year: keep reverse chronological
            year_events = sorted(events_by_year[year], key=lambda e: e[0], reverse=True)
            for ev in year_events:
                parts.append(format_bullet(ev))
            parts.append("")  # blank line between years
    else:
        parts.append("_No past events yet._")

    parts.append("")  # final newline
    return "\n".join(parts)


def update_meetups_file(section_markdown: str):
    if TARGET_FILE.exists():
        text = TARGET_FILE.read_text(encoding="utf-8")
    else:
        text = ""

    if SECTION_HEADER in text:
        # Patch existing section between SECTION_HEADER and first "* * *"
        before, sep, after = text.partition(SECTION_HEADER)
        body, sep2, rest = after.partition("* * *")

        if sep2:
            updated = before + section_markdown + "\n* * *" + rest
        else:
            updated = before + section_markdown
    else:
        # Create a minimal page from scratch
        updated = f"""---
layout: page
title: Affiliate Meetups — Aalto Machine Learning Group
permalink: /meetups12/
---

Our bi-weekly online seminar for affiliates and friends of the community.

* * *

{section_markdown}

* * *

Interested in presenting? Propose a 20–25 min talk (plus Q&A) when you register.
"""

    TARGET_FILE.write_text(updated, encoding="utf-8")


def main():
    ics_url = os.getenv(ICS_URL_ENV)
    if not ics_url:
        raise SystemExit(f"Environment variable {ICS_URL_ENV} not set")

    cal = fetch_calendar(ics_url)
    events = extract_events(cal)
    upcoming, past = split_upcoming_past(events)

    section_md = render_section_markdown(upcoming, past)
    update_meetups_file(section_md)


if __name__ == "__main__":
    main()
