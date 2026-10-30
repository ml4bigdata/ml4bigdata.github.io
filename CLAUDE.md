# CLAUDE.md — Aalto Machine Learning Research Group Website

## Overview

Jekyll-based research group website for the **Aalto Machine Learning Research Group**, led by Professor Alexander Jung. Deployed via **GitHub Pages** from the `main` branch.

- **Live site:** https://ml4bigdata.github.io
- **Repo:** ml4bigdata/ml4bigdata.github.io
- **Theme:** jekyll-theme-cayman (remote theme, customized via `assets/css/style.scss`)

## Build & Serve

```bash
bundle install            # first time / after Gemfile changes
bundle exec jekyll serve  # local dev server at http://localhost:4000
```

## Project Structure

```
├── _config.yml            # Jekyll config (title, theme, collections, plugins)
├── _layouts/              # HTML templates
│   ├── default.html       #   Main layout (nav bar, header, footer)
│   ├── home.html          #   Home page (extends default)
│   ├── page.html          #   Generic content page
│   └── post.html          #   Blog post
├── _pages/                # Content pages (Jekyll collection, output: true)
│   ├── people.md          #   Team directory
│   ├── research.md        #   Research areas & grants
│   ├── publications.md    #   Publications listing
│   ├── teaching.md        #   Courses & teaching philosophy
│   ├── meetups.md         #   Affiliate program events (auto-generated)
│   └── <name>.md          #   Individual team member profiles
├── _posts/                # Blog posts (currently unused)
├── assets/
│   ├── css/style.scss     # Custom SCSS overrides on Cayman theme
│   └── images/            # Photos, book covers, awards, PDFs
├── scripts/
│   └── update_meetups_from_ics.py  # Syncs meetups from Outlook calendar
├── .github/workflows/
│   └── update-meetups.yml # CI: auto-updates meetups 3x daily
├── index.markdown         # Home page content
├── Gemfile                # Ruby dependencies
└── .gitignore
```

## Content Conventions

### Adding a new team member

1. Create `_pages/<firstname>_<lastname>.md` with frontmatter:
   ```yaml
   ---
   layout: page
   title: Team members
   ---
   ```
2. Add photo to `assets/images/` (JPG/PNG, ~300px wide recommended).
3. Add entry to `_pages/people.md` under the appropriate section (Faculty / Post-Docs / PhD Students / TAs) linking to the new page.

### Page frontmatter

- Hub pages (research, teaching, etc.) use `permalink: /<slug>/` in frontmatter.
- Member pages rely on the collection permalink `/:path/` from `_config.yml`.

### Navigation

The nav bar is defined in `_layouts/default.html`. Current links: Home, Current Projects, People, Publications, Teaching, Affiliate Program.

## Automation

- **Meetups sync:** GitHub Actions workflow runs `scripts/update_meetups_from_ics.py` at 06:00, 12:00, 18:00 UTC daily. It fetches an Outlook ICS calendar (URL stored in repo secret `OUTLOOK_ICS_URL`) and regenerates `_pages/meetups.md`. **Do not manually edit the events section of meetups.md** — it will be overwritten.

## Style Notes

- The site uses a light/neutral color scheme (gray header, black headings, white background).
- Custom styles override Cayman defaults in `assets/css/style.scss`.
- Member pages use emoji section headers (Bio, Publications, Contact).

## Known Issues / TODOs

- `_config.yml` has placeholder values for `email`, `twitter_username`, `github_username`.
- `_posts/` contains only a default Jekyll welcome post (unused).
- `publications.md` is empty (just frontmatter).
- Several PhD students have "[To be updated]" thesis topics.
- Image files use inconsistent naming (mixed case, underscores vs no separators).
