# Weekly Instagram processing (run by a scheduled Claude task, Monday morning)

Posts are fetched on Sunday evening by `.github/workflows/instagram.yml` into the branch
`instagram-inbox` (`pending/<user>__<id>.json` + `_0.jpg`, `_1.jpg` … posters).
Your job: turn the posts that announce events into entries in `instagram/events.json` on `main`.

## Steps

1. `git fetch origin instagram-inbox main` and check out `main` (pull). Read the inbox with
   `git worktree add /tmp/inbox origin/instagram-inbox` (or `git show`). Nothing in `pending/` → stop.
2. For every `pending/*.json`: read the caption **and look at every image** (the date is often only on
   the poster). Decide per post:
   - **Event in Amsterdam with a date** (concert, club night, screening, dinner, talk, exhibition,
     market…) → add one entry per date. Posters listing a whole month → one entry per item.
   - Anything else (photos of last night, "thanks!", merch, vague "soon", events elsewhere) → skip.
   - **In doubt about the date or time → skip it**, or leave the time out (date only = all-day)
     rather than guessing. Never invent a time.
3. Year: the post's `timestamp` year, unless the date would then be more than ~2 months before the
   post (then next year).
4. Skip an event when it is already in `data/events.json` from a regular scraper (same venue, same day,
   similar title) – the venue's own agenda wins.
5. Entry format in `instagram/events.json` → `events`:
   ```json
   {"id": "<post id>" (add "-2", "-3" for more events from one post),
    "venue": "<venue from the inbox json, or the real venue named on the poster>",
    "title": "<clean title, no emoji/hashtags>",
    "subtitle": "<artists / short extra info or null>",
    "start": "2026-11-25T20:00"  (local time; "2026-11-25" when no time is given),
    "end": null | "2026-11-25T23:00" | "2026-12-06" (exhibitions/periods),
    "category": "film|music|club|talk|theatre|jazz|food|other",
    "price": "€ 5" | "gratis" | "op donatie" | null,
    "status": "normal" | "sold_out" | "cancelled",
    "url": "<permalink>", "added": "<today YYYY-MM-DD>"}
   ```
   Category rules as in CLAUDE.md (DJ/techno/clubnacht → club; dinner/volkskeuken → food).
   An update post ("cancelled", "sold out", "new time") changes the existing entry instead of adding one.
6. Remove entries whose `end` (or `start`) is more than 7 days in the past.
7. Validate: run `python run.py --only instagram` and check the log reports no invalid events.
8. Commit `instagram/events.json` on `main` (message "Instagram events <date>: N new") and push
   (`git pull --rebase` first; retry). This push triggers the site update.
9. On `instagram-inbox`: `git rm` the processed `pending/` files (keep `seen.json`), commit, push.
10. Report in Dutch, briefly: per account how many posts, which events were added, which posts you
    skipped because of doubt (with link), and any account that failed in the fetch log.
