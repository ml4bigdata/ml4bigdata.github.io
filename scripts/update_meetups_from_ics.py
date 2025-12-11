#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 09:40:03 2025

@author: junga1
"""

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
TARGET_FILE = Path("_pages/meetups.md")  # adapt if it's e.g. meetups/index.md
SECTION_HEADER = ""  # anchor text in your markdown
TZ = pytz.timezone("Europe/Helsinki")

YOUTUBE_PLAYLIST_URL = (
    "https://youtube.com/playlist?list=PLrbn2dGrLJK8wsi_vpr94Gzas7TzUsFNh&si=Y3bRndboTqN8zOc_"
)


def fetch_calendar(url: str) -> Calendar:
    resp = requests.get(url)
    resp.raise_for_status()
    return Calendar.from_ical(resp.content)


def extract_events(cal: Calendar):
    """Return list of (start_dt_aware, summary, location, url, description) for events."""
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

        # Description text (may be long; keep as-is for now)
        description = str(component.get("description", "")).strip()

        events.append((dt, summary, location, url, description))

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


def _clean_description(desc: str) -> str:
    """Collapse whitespace in description for nicer single-paragraph rendering."""
    if not desc:
        return ""
    # Replace newlines and multiple spaces with single spaces
    return " ".join(desc.split())


def format_bullet(ev, include_description: bool = False) -> str:
    dt, summary, location, url, description = ev
    # Example: "8 Aug 2025 — Title (Location) · [🎥 Recording](...)"
    try:
        date_str = dt.strftime("%-d %b %Y")  # Unix-like
    except ValueError:
        date_str = dt.strftime("%d %b %Y")   # Windows fallback

    text = summary or "(No title)"

    # Avoid printing the location if it's exactly the URL (e.g. YouTube/Zoom in location)
    if location and (not url or location.strip() != url.strip()):
        text += f" ({location})"

    if url:
        label = format_link_label(url)
        line = f"* {date_str} — {text} · [{label}]({url})"
    else:
        line = f"* {date_str} — {text}"

    if include_description:
        desc_clean = _clean_description(description)
        if desc_clean:
            # Indent by 4 spaces so it appears as a paragraph under the list item in Markdown
            line += f"\n    {desc_clean}"

    return line


def render_section_markdown(upcoming, past, ics_url: str) -> str:
    """Build the entire markdown block that will replace the section."""
    parts = []

    # --- ICS subscription link ---
    parts.append("### 📅 Subscribe to our calendar")
    parts.append(
        f"[Click here to subscribe to the Aalto ML Affiliate Meetup calendar]({ics_url})"
    )
    parts.append("")
    parts.append(
        "*Add this link to Google Calendar, Apple Calendar, Outlook, or any calendar app.*"
    )
    parts.append("")
    parts.append("---")
    parts.append("")

    # --- Upcoming ---
    parts.append("## Upcoming")
    if upcoming:
        for ev in upcoming:
            # For upcoming events, also show the description text (if any)
            parts.append(format_bullet(ev, include_description=True))
    else:
        parts.append("_No upcoming meetups scheduled. Stay tuned!_")
    parts.append("")

    # --- Past events (limit to 3 most recent) ---
    parts.append("## Past events")
    parts.append(
        f"For the full archive of recordings, see our [YouTube playlist]({YOUTUBE_PLAYLIST_URL})."
    )
    parts.append("")

    if past:
        # Keep only the 3 most recent past events
        limited_past = past[:3]

        events_by_year = defaultdict(list)
        for ev in limited_past:
            year = ev[0].year
            events_by_year[year].append(ev)

        # Show most recent years first
        for year in sorted(events_by_year.keys(), reverse=True):
            parts.append(f"#### {year}")
            # within each year: keep reverse chronological
            year_events = sorted(events_by_year[year], key=lambda e: e[0], reverse=True)
            for ev in year_events:
                # For past events, we keep the compact format without descriptions
                parts.append(format_bullet(ev, include_description=False))
            parts.append("")  # blank line between years
    else:
        parts.append("_No past events yet._")

    parts.append("")  # final newline
    return "\n".join(parts)


def update_meetups_file(section_markdown: str):
    updated = f"""---
layout: page
title: Affiliate Meetups — Aalto Machine Learning Group
permalink: /meetups/
---

Our bi-weekly online seminar for affiliates and friends of the community.

* * *

{section_markdown}

* * *

Interested in presenting? Propose a 20–25 min talk (email to first dot last...)
"""
    TARGET_FILE.write_text(updated, encoding="utf-8")


def main():
    ics_url = "https://outlook.office365.com/owa/calendar/717f97a819e846ce9ba3333552f2b2b9@aalto.fi/94f082defbce42a39f4f0a8125c6c8322669307906715889367/calendar.ics"
    if not ics_url:
        raise SystemExit(f"Environment variable {ICS_URL_ENV} not set")

    cal = fetch_calendar(ics_url)
    events = extract_events(cal)
    upcoming, past = split_upcoming_past(events)

    section_md = render_section_markdown(upcoming, past, ics_url)
    update_meetups_file(section_md)


if __name__ == "__main__":
    main()
