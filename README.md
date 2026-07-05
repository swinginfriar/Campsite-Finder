# CampSage 🏕️

Finds great **California** campsites with **2–3 consecutive nights open at the same site**,
ranked **closest-to-home first** among **well-reviewed** spots, and publishes a phone-friendly
status page + an interactive map. Runs on any always-on box via cron. **No API keys.**

## Quick start
```bash
pip install flask                 # the only dependency (scanner itself is stdlib-only)
# 1. set your home location + search radius in config.py (HOME_LAT / HOME_LNG / ...)
python3 camp_agent.py             # scan recreation.gov + ReserveCalifornia -> writes status.json
python3 camp_wiki_images.py       # (optional) fetch beach/park photos from Wikimedia Commons
python3 campsage_web.py           # serve it -> open http://localhost:5001/camp  (and /camp/map)
```
Run `camp_agent.py` on a cron (e.g. a few times a day) to keep results fresh. Add the page to your
phone's Home Screen. Every card has a green **Book on Recreation.gov →** button, a **See calendar**
link, and **Directions**.

## Run with Docker (Dockhand / Portainer / plain compose)
Clone the repo into your Dockhand instance and bring the stack up — no host Python, no cron, no
API keys, **and no environment variables to configure**:
```bash
docker compose up -d --build      # then open http://<host>:5001/camp
```
Two services share one image and a persistent `campsage-data` volume:
- **`web`** — serves the phone page, map, and settings on port **5001** (remap the left side of
  `"5001:5001"` in `docker-compose.yml` to change the host port).
- **`scanner`** — runs the scan on start and re-runs on the interval you set, replacing the cron.
  Writes `status.json` / `dashboard.html` to the volume that `web` reads.

### Configure everything in the browser — no env vars
Open **`/camp/settings`** (linked from the top of the list, map, and placeholder pages) to set your
home base, search radius, rating bars, search window, weekends-only, scan interval, and photo
fetching. Settings are saved to `settings.json` on the `campsage-data` volume, and the scanner picks
them up on its next run. Hit **Save & scan now** to kick a fresh scan within a few seconds instead of
waiting out the interval.

Ships with sensible Los Angeles defaults, so it boots and works with **zero configuration** — just
open Settings and change the home base to yours.

The scanner's first run takes a couple minutes; until it finishes `/camp` shows a placeholder with a
link to Settings. `docker compose logs -f scanner` shows scan progress.

### The one bootstrap variable (you don't set it)
The image bakes in `CAMPSAGE_DATA_DIR=/data` so the app knows where the volume is mounted. It's
infrastructure, set on the image — not something you configure. (For a plain local run outside Docker
it's unset and defaults to `~/campsage`.) Everything a user would actually tune lives in the UI.

## The map (`/camp/map`)
Interactive Leaflet map (OpenStreetMap tiles, **no key**) of every open site — filter by
type / nights / weekend / sought-after / region; tap a pin for photos, the exact **open dates + site
numbers**, and a booking link. Beach/state-park photos come from Wikimedia Commons (keyless).

## Place tabs
A scrollable tab strip groups every campground by **destination region** (Big Bear, Lake Arrowhead,
Ojai, Orange County Coast, …). Each campground is tagged with its nearest anchor in
`config.REGION_ANCHORS` by lat/lng; only regions that have campgrounds in range become tabs,
ordered closest-first. Tabs: **All** · **🏖️ Beaches** · one per region. A 📍 chip on each card
shows its region. All cards live in one `#grid`; tabs filter, the sort bar sorts.

## Social score (number + stars)
Every card shows a **social buzz** score — a 0–5 number + stars derived from YouTube (how many
videos + total views for "<name> camping"), via `socialscore.py`. It's POPULARITY, not
satisfaction, and labelled that way. Live Reddit/IG/TikTok scraping is impossible (they 403
datacenter IPs), so this is the honest no-key signal; scores are cached ~2 weeks so the scan stays
light. Sortable via the "Social buzz" button. Plus the 💬 Reviews link row (Reddit/YouTube/TikTok/
Google searches) per card.

## Sections on the page
1. **⛰️ All campgrounds** — 2–3 night openings, closest-to-LA first. Sort: Closest /
   Best reviewed / Most reviewed / Highest rated / Soonest.
2. **🏖️ Beach camping — state beaches** — MAINLAND drive-up California state beaches
   (Leo Carrillo, San Onofre, Carpinteria, El Capitán, Refugio, Pismo, …) via **ReserveCalifornia**.
   Island camping is excluded. The state-park system has no review scores, so this ranks by
   **closest** + **soonest** + **most sites open**. Own sort bar; Book button → ReserveCalifornia.
3. **🧭 Booking concierge** + **Also great nearby — currently full**.

The beach source is `reservecalifornia.py` — it reverse-maps the same RDR API the
reservecalifornia.com site uses (`search/place` for nearby parks + distance, `search/grid` for
per-night `IsFree` availability). No API key. Base URL is read from the site's own config.json.

"Best reviewed" = `rating × log10(reviews+1)` — credibility-weighted, so a 4.7★/986-review spot
beats a 4.6★/5-review one. "Most reviewed" = raw count.

**Social reviews:** every card has a 💬 Reviews row (Reddit / YouTube / TikTok / Google) that
opens a search pre-filled with the campground name. These are deep links, not scraped — Reddit,
Instagram, and TikTok all 403 datacenter IPs, so live fetching is impossible/unreliable; the
links open on the phone where the user is logged in and get real results every time.

## How it works
- **Data:** recreation.gov public JSON — `search` (ratings, review counts, drive distance,
  lat/lng) + `availability` (per-night status per site, so consecutive nights are detectable).
- `camp_agent.py` discovers campgrounds within `MAX_DISTANCE_MI` of `HOME_*`, keeps the
  well-reviewed ones (`MIN_RATING`/`MIN_REVIEWS`, plus a high-rating "gem" tier), fetches each
  campground's availability across the window in parallel, finds each site's earliest run of
  2–3 available nights, ranks closest-first, and writes:
  - `~/campsage/status.json` — machine-readable results
  - `~/campsage/dashboard.html` — the self-contained page served at `/camp`
- `ai_concierge.sh` asks Claude (on the **subscription**, no API cost) for booking tips specific
  to the current top spots → `~/campsage/booking_tips.json` (shown under "Booking concierge").

## Tuning
Everything is in `config.py`: home base, max distance, rating bars, window length, nights
(`NIGHTS=[3,2]`), `WEEKENDS_ONLY`. Edit and re-run `python3 camp_agent.py`.

## Cron (Pacific, in `crontab -l`)
- `camp_agent.py` at **7:00 / 13:00 / 18:00** (7am catches recreation.gov's rolling 6-month
  release; midday + evening catch cancellations).
- `ai_concierge.sh` at **7:10** (subscription tips refresh).

## Validate
`python3 selftest.py` — checks the live API, freshness, sort/distance/rating/nights invariants,
that a claimed opening is *independently* still available, `/camp` serves, and cron is installed.
Exit 0 = all pass.

## Notes
- Single-site **group** campgrounds can show "1 site open" and get booked in minutes — book fast.
- Coverage is recreation.gov (national forests, NPS, etc.). California **state parks**
  (ReserveCalifornia) are a separate system not yet included — a future add.
