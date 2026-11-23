# Amsterdam Agenda

Personal site that collects events from favourite Amsterdam venues into one calendar.
Python scrapers → `data/events.json` (+ `status.json`, `events.ics`) → static Dutch site in `site/`
→ GitHub Pages, refreshed weekly by `.github/workflows/update.yml` (Monday 06:00 Europe/Amsterdam).

## Layout

```
scrapers/            one module per venue (+ shared helpers starting with "_")
  base.py            Event schema, date/category helpers, parse_ics, is_run/run_span
  http.py            polite Client: UA, 1.5 s delay per host, 6 h disk cache, Playwright render()
  _koepel.py         shared: The Movies + Filmhallen (/fk-feed/agenda JSON)
  _peppered.py       shared: Bellevue, Kleine Komedie, Frascati (Playwright, BunnyCDN JS check)
  _weticket.py       shared: WeTicket storefront RSS feeds (Skatecafé, Garage Noord, Ingang)
  _radar.py          shared: one Radar group per venue (Vrankrijk, Joe's Garage, Molli Chaoot, MKZ)
  _stager.py         shared: Stager shop JSON-LD (Nachbar, Radion)
  _nuxt.py           evaluates Nuxt `window.__NUXT__` payloads with node (Rialto, ITA)
recurring.json       hand-edited weekly items (food nights at places without an agenda, e.g. De Sering)
run.py               runs all scrapers, validates, dedupes, keeps 6 weeks, writes data/
ics.py               writes data/events.ics
build.py             assembles _site/ (site/ + data) for GitHub Pages
site/                index.html, style.css, app.js – plain JS, no build step, Dutch UI
tests/fixtures/      one raw sample per venue (exactly what fetch() returned)
RECON.md             data-source research per venue (method, difficulty, quirks)
```

## Commands

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q                               # parsers vs fixtures (fast, offline)
python run.py                                     # all scrapers (~4–5 min, uses .cache/)
python run.py --only melkweg --save-fixtures -v   # one venue, refresh its fixture
python build.py && (cd _site && python -m http.server 8000)   # preview the site
```
Playwright: pinned `playwright==1.63.0` (matches the preinstalled Chromium here). In CI the
workflow runs `playwright install --with-deps chromium`. `_nuxt.py` needs `node` on PATH.

## Event schema (`scrapers/base.py: Event`)

| field | type | notes |
|---|---|---|
| `id` | str, required | `<module NAME>-<native id>`; stable across runs (use `make_id`) |
| `title` | str, required | clean text (use `clean()`), no "SOLD OUT" prefixes |
| `venue` | str, required | real venue name (Paradiso module yields Paradiso/Tolhuistuin/Bitterzoet/…) |
| `start` | aware datetime | Europe/Amsterdam; serialised as ISO 8601 with offset |
| `end` | datetime \| None | optional; must be ≥ start |
| `category` | `film \| music \| club \| talk \| theatre \| jazz \| food \| other` | food = dinners, volkskeukens, eetcafé nights |
| `url` | str, required | event page (fallback: agenda page) |
| `status` | `normal \| sold_out \| cancelled \| moved` | waiting list counts as sold_out |
| `price` | str \| None | display text, e.g. `€ 15` or `€ 10,75–€ 25,00`, `gratis` |
| `image` | str \| None | absolute URL |
| `kind` | `event \| series \| weekly` | **series** = themed period/run spanning `start..end` ("Loopt nu" banner, all-day in ics); **weekly** = fixed recurring item, `subtitle` says when ("Vaste prik" row, not in ics) |
| `all_day` | bool | only the date is known (start is 00:00); site shows "–" |
| `subtitle` | str \| None | company / support act / series name / hall |
| `source` | str | set by run.py = module NAME |

Validation (`Event.validate`) runs in run.py; invalid events are dropped with a warning.

## Ground rules / user preferences

- **Cinemas: no regular screenings.** Only specials (previews, Q&A, intro, live broadcasts, marathons,
  double bills, late-night) and themed periods as `kind="series"` (e.g. Filmhallen "Nineties",
  Rialto Shaw Brothers, Eye retrospectives). Filmhuis Cavia is all curated → everything counts.
- Theatre/film **runs** (many performances close together, `is_run`) → one series; monthly recurring
  shows stay individual events. Skip performances at other locations (tours). Exception: **ITA lists
  every performance** (user wish, `ita.GROUP_RUNS = False`).
- **Food** is its own category. Repeating food items (lunch/dinner/eetcafé) → `collapse_recurring` →
  kind="weekly". Places without an agenda but with fixed food nights go in `recurring.json`.
- Radar (squat.net) city-wide is declined by the user; per-venue Radar groups are fine (`_radar.py`,
  used for Vrankrijk and Joe's Garage, whose own sites show that same agenda). Don't use DJGuide (blocks automated access on
  purpose) or Instagram (login wall). For small clubs, look for a ticket shop with a feed first:
  `<name>.weticket.io` exposes `api.weticket.io/storefront/organizations/<uuid>/events.xml`;
  `<name>.stager.co/shop/<name>` has schema.org Event JSON-LD; WordPress "The Events Calendar" sites
  have `?post_type=tribe_events&ical=1`. Ticketswap is resale – not used as a source.
- **Never bypass bot protection** (Cloudflare Turnstile, "One moment, please…" pages, stealth tricks,
  UA spoofing to dodge blocks). The client raises `BlockedError` on such pages. A plain headless
  browser that passes a JS check (BunnyCDN `/csq/`) is fine. If a site blocks us: set `ENABLED = False`
  + `DISABLED_REASON`, document it in RECON.md and tell the user (Kriterion → Filmvandaag; LAB111 off).
- Be polite: use `Client` (identifying UA, delay, cache); keep request counts low; weekly run.
- One scraper failing must never break the run – just raise; run.py logs it into status.json and keeps
  that source's events from the previous run (footer shows "(oud)"). Empty responses are retried twice (10 s, 30 s); the workflow rebases + retries its data push so the fallback data is never lost.

## How to add a venue ("add venue X")

1. **Recon** (record in RECON.md table): look for, in this order: iCal/RSS or a public JSON API
   (page source, `wp-json`, `/fk-feed/`, Next `__NEXT_DATA__`/RSC, Nuxt `__NUXT__`, XHRs via
   Playwright) → JSON-LD → plain HTML → Playwright. Check bot protection with a plain request first.
2. **Module** `scrapers/<name>.py` (file name == `NAME`):
   ```python
   NAME = "venuename"          # id prefix + status key
   VENUE = "Display Name"      # default venue name
   HOMEPAGE = "https://…"      # shown in the footer
   # ENABLED = False; DISABLED_REASON = "…"   (optional)

   def fetch(client, today: date):        # network only; return str | list | dict (JSON-able)
       return client.get_json(URL)        # or get_text / post_json / render(url, wait_selector=…)

   def parse(raw, today: date) -> list[Event]:   # pure: no network, deterministic for a given today
       ...
   ```
   Keep `fetch()` output small (trim HTML to the relevant part) – it becomes the fixture.
   Reuse helpers: `clean`, `make_id`, `parse_iso(…, assume_local=)`, `local`, `infer_year`,
   `month_number` (NL/EN), `parse_hhmm`, `guess_category`, `parse_ics`, `is_run`, `run_span`.
   For yearless dates use `infer_year` (or weekday matching like `nieuweanita.resolve_date`).
3. **Fixture + test**: `python run.py --only <name> --save-fixtures -v`, then add `test_<name>` to
   `tests/test_venues.py` with a few concrete assertions (title, exact start, category, status).
   `tests/test_all_scrapers.py` automatically checks the module contract against the fixture.
   Fixture date is fixed: `FIXTURE_DATE = 2026-11-23` in `tests/conftest.py` – if you refresh
   fixtures on another day, update it and the dated assertions.
4. **Run & check**: `python -m pytest -q`, `python run.py --only <name>`, inspect `data/events.json`
   (counts per category/status, times in local time, no regular cinema screenings, no duplicates),
   `python build.py` and look at the site on a phone-sized viewport.
5. If the venue is also covered by an aggregator (jazzin), add it to `jazzin.OWN_SCRAPER_VENUES`.
6. Update the RECON.md table (method, difficulty, notes) and commit.

## Site filters

"Vaste prik" (kind=weekly) is a collapsible list grouped per weekday (Maandag…Zondag, items repeated on
each day they run, sorted by time; open/closed remembered). Days/time are parsed from the subtitle
"Elke wo, do 12:00 · …" – keep that format in scrapers and recurring.json.
Quick periods, categories, venues (+ ★ favourites), search, and a **club switch** (Aan / Alleen / Uit,
stored in localStorage). `guess_category` only says "club" for real club words (clubnacht, DJ, techno…),
not for a bare "club" (Club Amsterdam Klezmer, book club).

## Quirks worth remembering

- De Balie `vo.date_time_raw` says `+00:00` but is local time → `parse_iso(…, assume_local=True)`.
- Melkweg `isPublished: false` means "ticket sale closed" (sold out/cancelled), not hidden.
- Paradiso GraphQL: `site=paradisoNederlands`, paginate with `searchAfter` = last `sort`;
  public token from paradiso.nl JS (use approved by the user).
- De Nieuwe Anita homepage grid is unreliable → REST list + detail pages (weekday pins the year).
- Peppered theatres list tour dates elsewhere; `data-event-start` on order buttons is exact.
- Rialto 'verwacht' programs are placeholders (00:00, location "Onbekend.") → not events.
