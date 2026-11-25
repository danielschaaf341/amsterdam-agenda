# Weekly Instagram check in the user's own Chrome (Claude desktop app + Claude in Chrome)

Runs as a scheduled task on the user's laptop, Monday ~05:00, in the local clone of this repo.
The user is logged in to Instagram in Chrome. **Behave like a person browsing:** open profiles one
at a time, no rapid clicking, no scrolling far back, never log in/out, never like/follow/comment/DM,
never change account settings. If Instagram shows a challenge, captcha, "try again later" or a login
prompt: **stop immediately**, don't try to get around it, and report it.

## Steps

1. `git pull` in the repo. Read `instagram/accounts.json` and `instagram/events.json`.
   `instagram/last_check.json` (if present) has per account the newest post date seen last time.
2. For each account with a `username`: open `https://www.instagram.com/<username>/` in a new tab.
   Open the posts (pinned posts too) published since the last check (max ~2 weeks, max 9 posts).
   Read the caption **and look at the poster image(s)** – the date is often only on the poster.
   Close the tab before the next account. Pause a few seconds between accounts.
   Accounts with `username: null`: search the venue name once on Instagram; put the likely handle
   in the report (don't write it to accounts.json – the user confirms).
3. Decide per post, following `instagram/PROCESS.md` steps 2–6 (what counts as an event, year
   rules, skip duplicates of `data/events.json`, the entry format, removing past entries).
   `id` = the post shortcode from the URL (`/p/<shortcode>/`), `url` = the post URL.
   In doubt about date/time → skip (or date only). Never invent a time.
4. Update `instagram/last_check.json` (`{"<username>": "<YYYY-MM-DD of newest post>"}`).
5. `python run.py --only instagram` must report no invalid events.
6. Commit `instagram/events.json` + `instagram/last_check.json`
   ("Instagram events <date>: N new"), `git pull --rebase`, push. This push updates the site.
7. Report in Dutch, short: events added (venue, date, title), posts skipped because of doubt
   (with link), accounts without new posts, handles found for `null` accounts, any problem.
