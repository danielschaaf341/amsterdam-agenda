# RECON – Amsterdam venue data sources

Recon date: 2026-11-23. Build status updated after phase 2–4 (see "Status" column).

## Status after building (2026-11-23)

| venue | module | final method | status |
|---|---|---|---|
| Paradiso (+Tolhuistuin, Bitterzoet, other Paradiso shows) | `paradiso` | GraphQL API (public token from site JS, approved by user) | ✅ ~140 events / 6 wk |
| Melkweg | `melkweg` | `__NEXT_DATA__` JSON | ✅ |
| Pakhuis de Zwijger | `zwijger` | HTML, `?page=N` | ✅ |
| OCCII | `occii` | iCal `/events.ics` | ✅ |
| The Movies | `themovies` | JSON `/fk-feed/agenda`, specials + themes only | ✅ (few specials) |
| Filmhallen *(added on request)* | `filmhallen` | same feed as The Movies | ✅ incl. "Nineties" series, opera/ballet live |
| De Balie | `debalie` | WP REST (`vo-programme`; `vo-cinema` only `special: true`) | ✅ |
| Felix Meritis | `felixmeritis` | `/wp-json/vo/v1/events?upcoming=true` | ✅ |
| OT301 | `ot301` | Amsterdam Alternative JSON (venue 105), per month | ✅ |
| De Rode Hoed | `rodehoed` | Inertia page JSON (`script[data-page]`) | ✅ |
| De Nieuwe Anita | `nieuweanita` | WP REST list + detail pages (~100 req, cached) | ✅ homepage grid turned unreliable |
| jazzin.amsterdam | `jazzin` | RSC payload; venues with own scraper skipped | ✅ ~190 jazz events |
| Filmhuis Cavia | `cavia` | monthly HTML pages | ✅ |
| Rialto | `rialto` | Nuxt payload of `/nl/specials/*` (node vm) | ✅ series + voorpremières |
| Theater Bellevue | `bellevue` | Playwright (BunnyCDN JS check), Peppered parser | ✅ |
| De Kleine Komedie | `kleinekomedie` | same | ✅ |
| Frascati | `frascati` | same | ✅ |
| ITA / Stadsschouwburg | `ita` | Nuxt payload, `?page=N` | ✅ |
| Eye Filmmuseum | `eye` | RSC payload of `/whats-on` → themed programmes as series | ✅ (no single screenings) |
| Kriterion | `kriterion` | **via Filmvandaag JSON-LD** (kriterion.nl = Cloudflare Turnstile) | ⚠️ thin: Sneak Preview + late-night |
| LAB111 | `lab111` | WP REST + post pages – written & tested, **disabled** | ⛔ site serves a bot-check page to our identified UA |
| Garage Noord *(added)* | `garagenoord` | WeTicket RSS feed (garagenoord.weticket.io) – exact times | ✅ incl. "bar40" nights |
| Skatecafé *(added)* | `skatecafe` | WeTicket RSS feed (skatecafe.weticket.io); skatecafe.nl itself = bot check | ✅ |
| Ingang *(added)* | `ingang` | WeTicket RSS feed (ingang.weticket.io) | ✅ (few events) |
| FC Hyena *(added)* | `fchyena` | /films → Specials collection → /specials/<slug> prose dates + "elke derde dinsdag" rule | ✅ specials only (thin) |
| Café 40 | – | probably Garage Noord's bar (Gedempt Hamerkanaal **40**; "bar40 hosted by…") → covered by `garagenoord` | ➖ |
| Nachbar *(added)* | `nachbar` | schema.org Event JSON-LD on its Stager shop (nachbar.stager.co) | ✅ club nights + prices |
| Café Voorwaarts *(added)* | `cafevoorwaarts` | The Events Calendar iCal feed (`?post_type=tribe_events&ical=1`) | ✅ (few events) |
| Amsterdam Alternative network *(added)* | `amsterdamalternative` | AA JSON service without venue filter, per month (slow server) | ✅ ~22 venues: Cinetol, Plein Theater, Teatro Munganga, Splendor, Nieuwland, Badhuistheater, ADM, Vondelbunker, … |
| Tolhuistuin own programme *(added)* | `tolhuistuin` | `:all-items` JSON on /agenda; Paradiso concerts skipped | ✅ |
| Carré *(added)* | `carre` | site JSON `/api/render/production-page-list-nl` | ✅ runs → series |
| De Sering | `recurring` (recurring.json) | desering.org = Cloudflare; GitHub Pages mirror is stale (Dec 2025) | ➖ community kitchen as weekly "food" item |
| DJGuide (aggregator) | – | blocks automated access from hosting networks on purpose (403 + robots.txt) → not used | ✗ |
| Spui25 | – | Cloudflare Turnstile; uva.nl has no usable Spui25 feed | ⛔ not built |
| Radar (squat.net) | – | public API works | ✗ declined by user |

---

## Original recon (phase 1)

All endpoints below were fetched from a plain cloud container (no cookies, no login).
"Plain HTTP" means `requests` with an identifying user agent works; "Playwright" means a real browser is needed.

**Scope rule for cinemas** (user request): regular screenings are *not* wanted. From cinemas we only take
special events (Q&A, premières/previews, double bills, marathons, festivals, live-score, parties) and
*themed periods* (retrospectives / series such as "90s month" or "Eye Classics"), shown as a running series.

## Summary table

| # | venue | agenda URL | method | difficulty | notes |
|---|---|---|---|---|---|
| 1 | Melkweg | https://www.melkweg.nl/nl/agenda/ | 2 – JSON in HTML (`__NEXT_DATA__`) | easy | One request: `props.pageProps.pageData.attributes.content[0].attributes.initialEvents` → 257 events, Oct 2026 → Dec 2027. Fields: `name`, `startDate`/`endDate` (UTC), `profile` (Concert/Clubnacht/Film/Expositie/Festival), `tags`, `isSoldOut`, `isCancelled`, `isMovedToNewDate`, `url`, `media.featuredImage`. No price. |
| 2 | OCCII | https://occii.org/events.ics | 1 – iCal | easy | WordPress Events Manager iCal feed: 17 upcoming events (to May 2027), `CATEGORIES` (music, course/workshop…), `URL`. Times in UTC (`Z`). Avoid `/events/?ical=1` (4 MB, full archive since 2013). |
| 3 | The Movies | https://themovies.nl/fk-feed/agenda | 1 – public JSON | easy | Feed used by the site itself; dict of films → `times[]` with `program_start`/`program_end` (`YYYYMMDDHHMM`, local), `ticket_status`, `location`, per-show `tags` (`Preview`, `No subs`). Film `tags`: `Première`, `+Extra`, `Klassieker`, `Monumental`, `Laatste kans`. **Specials only**: keep shows tagged Preview or films tagged +Extra/Première/Klassieker/Monumental. WP REST is locked. |
| 4 | De Balie | https://debalie.nl/wp-json/wp/v2/vo-programme | 1 – WP REST JSON | easy | Custom `vo` field: `date_time_raw` (**labelled +00:00 but is local time**), `time`, `price`, `status`, `available_tickets`, `category`, `featured_image`, `ticket_link`. Ordered by publish date → page through (`per_page=100`) and filter upcoming. `vo-cinema` holds the film schedule (skip, except specials). |
| 5 | Felix Meritis | https://felixmeritis.nl/wp-json/vo/v1/events?upcoming=true | 1 – JSON API | easy | Same agency plugin as De Balie. Paginated (`page=N`, `last_page` flag). Fields `post_title`, `vo_date` (`do 26 nov`, **no year**), `vo_time`, `vo_large_image`, `post_name` → URL `/programma/<slug>/`. |
| 6 | OT301 | https://amsterdamalternative.nl/services/get-events-past-v25.php?venue=105&month=11&months=2 | 1 – public JSON | easy | ot301.nl loads its agenda from Amsterdam Alternative (venue 105). Fields: `start` (unix), `title`, `lineup`, `venue_room`, `type.label` (Concert, Film, Electronic music/party, Food/kitchen…), `price`. Drop `Food, kitchen`/`Bar`. Page caps at `rows: 25` → query month by month. Also covered by Radar. |
| 7 | Rode Hoed | https://rodehoed.nl/programma/ | 3 – HTML | easy | Static HTML, 8 items: `MA 23.11.2026`, title, topics, time, `€ 15`, `Uitverkocht`. All on one page. |
| 8 | Radar (squat.net) | https://radar.squat.net/api/1.2/search/events.json?facets[city][]=Amsterdam | 1 – public JSON API | easy | 925 upcoming Amsterdam events; `date_time[]` (`time_start`/`time_end` with offset, `rrule`), `offline[].title` (venue + address), `category[].name`, `price`, `url`. Covers OT301, Cavia, OCCII, De Nieuwe Anita, Vrankrijk, Joe's Garage, Vondelbunker, NieuwLand… **Lots of recurring noise** (study café, volkskeuken) → filter on category and skip weekly recurrences. Dedupe against OCCII/OT301/Anita/Cavia. |
| 9 | Pakhuis de Zwijger | https://dezwijger.nl/agenda?page=N | 3 – HTML | easy-medium | WP REST locked (401). 20 `.program.teaser` cards per page: `.suptitle`, `.title`, `.subtitle`, `.date-time` (`Vandaag, 20.00` / `Morgen, 19.00` / `do 26 nov, 19.30` – relative + yearless), `.location`, ticket link. Detail pages have no JSON-LD. Internal `/ajax/agenda/getItems` exists (not needed). |
| 10 | De Nieuwe Anita | https://denieuweanita.nl/ | 3 – HTML | easy-medium | WP REST `/wp/v2/agenda` has no event dates. Homepage lists the full agenda (65 items, ~4 months) in date order: `.post_title`, `_space_yearless_date` (`23 Nov`), `agenda_time_start`, category as icon. Year inferred from rollover. |
| 11 | Paradiso (+ Tolhuistuin, Bitterzoet) | https://www.paradiso.nl/ | 4 – Playwright (capture its own XHR) | medium | Next.js RSC. First ~25 events (≈5 days) are embedded as JSON (`title`, `startDateTime` with offset, `subtitle`, `soldOut`, `eventStatus`, `location.title` = Paradiso/Tolhuistuin/…). Later pages load from a GraphQL API (`programItemsQuery`, AWS API Gateway) using a public bearer token embedded in the site JS. **Calling that API directly is the cleanest option but needs your OK** (see questions). Otherwise: Playwright scrolls the page and we read the GraphQL responses the browser receives. |
| 12 | Lab111 | https://www.lab111.nl/wp-json/wp/v2/posts?categories=116,79 | 1 + 3 – WP REST + HTML | medium | Specials only: categories `events` (116) and `specials` (79) → e.g. *LOTR 25th Anniversary*, *Dune double bill incl. lunch*, *10th Anniversary Party*, *Sing-Along: Labyrinth*, festivals. Post date ≠ event date: fetch each post page and parse its showtime list (`zo 13 dec 12:00 LAB 2 SOLD OUT`). `/programma/` once returned a "One moment, please…" bot page → keep the rate low. |
| 13 | Jazzin.amsterdam | https://jazzin.amsterdam/ | 2 – JSON in HTML (RSC payload) | medium | Jazz aggregator (Bimhuis, Kompaszaal, Zaal 100, Café de Pianist, Splendor, Volkshotel, ZOJazz…). Clean objects: `title`, `date`, `time`, `venue`, `price`, `site` (venue URL), `source`, `id`. ~1 month ahead, ~200 items. Need to un-escape the RSC string. `venue` = real venue (not "jazzin"). |
| 14 | Filmhuis Cavia | https://www.filmhuiscavia.nl/programma/november-2026 | 3 – HTML (or Radar) | medium | Concrete CMS, one page per month (`/programma/<month>-<year>`) + festival pages. Hand-written text: `Maandag 2 november, 18:30 | SPECIAL | title`. Irregular formatting. All curated (series/festivals) so all count as "special". **Alternative: take Cavia from Radar** (it's listed there) → easy. |
| 15 | Rialto | https://depijp.rialtofilm.nl/nl/specials | 2 – JSON in HTML (`window.__NUXT__`) | medium | rialtofilm.nl redirects to depijp.rialtofilm.nl (locations: De Pijp, Silo, VU Griffioen). Specials page lists series: *Rumble in Hong Kong with the Shaw Brothers*, *Makandra*, *Rialto for Short*, *Klassiek*, *Voorpremières*, *Kinderfilms*. Data is in a `window.__NUXT__=(function(a,b,…){…})(…)` IIFE → evaluate it (Node/Playwright `page.evaluate`) rather than regex. |
| 16 | Eye Filmmuseum | https://www.eyefilm.nl/whats-on | 2 – JSON in HTML (RSC payload) | medium-hard | Next.js. `/programma` and `/programma/agenda` return 404. `/whats-on` embeds programme items (retrospectives like *Ulrich Seidl*, *Charles Burnett*, *Eye Classics*) with start/end dates → fits the "themed period" concept well. Individual showtimes aren't in the SSR HTML. Parse series + date ranges; per-screening data would need more digging. |
| 17 | ITA (Stadsschouwburg) | https://ita.nl/nl/agenda-stadsschouwburg | 2 – JSON in HTML (`window.__NUXT__`) | medium-hard | Same agency as Rialto (cre8ion). 234 results; data in `__NUXT__` IIFE (~68 datetimes in first payload; probably paginated). `api.ita.nl` exists, but its endpoints aren't visible in the bundle. Evaluate `__NUXT__` in Node/Playwright; check pagination in phase 2. |
| 18 | Theater Bellevue | https://www.theaterbellevue.nl/agenda | 4 – Playwright | medium | BunnyCDN JS check (`/csq/` redirect, `x-redirect-reason: no-token`) blocks plain HTTP; a normal Playwright browser passes. Markup `.eventCard` / `.subshow`: title, company, `di 24 nov`, time, genre, price, `Wachtlijst`, `reprise`. First load shows ~8 productions → scroll/"load more". |
| 19 | De Kleine Komedie | https://www.dekleinekomedie.nl/agenda | 4 – Playwright | medium | Same CMS + BunnyCDN check as Bellevue → **share one parser**. |
| 20 | Frascati | https://www.frascatitheater.nl/nl/agenda | 4 – Playwright | medium | Same CMS + BunnyCDN check as Bellevue → shared parser. |
| 21 | Kriterion | https://www.kriterion.nl/ | ✗ blocked | hard | Cloudflare Turnstile ("Just a moment…"): 403 for curl **and** headless Playwright. I won't try to bypass it. Needs another source (see questions). |
| 22 | Spui25 | https://spui25.nl/agenda | ✗ blocked | hard | Same Cloudflare Turnstile as Kriterion. |

## Proposed build order (easiest first)

Phase 2 starts with Paradiso, Melkweg and De Zwijger as requested. After that:

OCCII → The Movies → De Balie → Felix Meritis → OT301 → Rode Hoed → Radar → De Nieuwe Anita → Lab111 →
Jazzin → Cavia → Rialto → Bellevue/Kleine Komedie/Frascati (one parser) → ITA → Eye → (Kriterion, Spui25 if a source is found)

## Overlaps / dedup

- Paradiso agenda includes **Tolhuistuin** and **Bitterzoet** (`location.title`) – no separate scrapers.
- **Radar** overlaps with OCCII, OT301, Cavia and De Nieuwe Anita → venue-specific source wins; Radar events at those venues are dropped.
- **Jazzin** is an aggregator → its `venue` field becomes the event's venue.
- De Balie, Felix Meritis: same WordPress plugin (`vo`) → small shared helper.
- Rialto and ITA: same Nuxt setup → shared `__NUXT__` evaluator.

## Cross-cutting findings

- Timezones vary: UTC (`Z`, Melkweg, OCCII), offsets (Paradiso, Radar), naive local (The Movies, Jazzin) and *mislabelled* (De Balie `+00:00` = local). Every scraper normalises to Europe/Amsterdam.
- Yearless dates (De Zwijger, Felix, Anita, Bellevue group): infer the year by "next occurrence from today".
- Themed periods (Eye series, Rialto specials, Lab111 festivals) need a representation for "runs from X to Y" → proposal: `kind: "event" | "series"` with `start`/`end` spanning the period.
