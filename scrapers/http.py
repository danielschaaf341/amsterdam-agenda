"""Polite HTTP client shared by all scrapers.

- identifies itself with a clear user agent
- waits between requests to the same host
- caches responses on disk (default 6 hours) so re-runs during development don't hit venues again
- renders JS-heavy / bot-checked pages with Playwright when a scraper asks for it
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

log = logging.getLogger("http")

USER_AGENT = os.environ.get(
    "AGENDA_USER_AGENT",
    "AmsterdamAgendaBot/1.0 (personal event calendar; polite: 1 req/1.5s, weekly run)",
)
# Browser-like UA for Playwright pages, still carrying our bot identifier.
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36 AmsterdamAgendaBot/1.0"
)
CACHE_DIR = Path(os.environ.get("AGENDA_CACHE_DIR", Path(__file__).resolve().parent.parent / ".cache" / "http"))


# Text of anti-bot interstitials. We never try to get past these; the scraper just fails clearly.
BOT_PAGE_MARKERS = ("<title>One moment, please...</title>", "<title>Just a moment...</title>",
                    "<title>Even geduld")  # Studio/K sometimes serves a wait/reload page


class BlockedError(RuntimeError):
    """The site answered with a bot-check page instead of content."""


class Client:
    def __init__(self, delay: float = 1.5, cache_ttl: float | None = None, use_cache: bool = True):
        self.delay = delay
        self.cache_ttl = cache_ttl if cache_ttl is not None else float(os.environ.get("AGENDA_CACHE_TTL", 6 * 3600))
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "nl,en;q=0.8"})
        self._last_request: dict[str, float] = {}
        self._pw = None
        self._browser = None
        self.requests_made = 0

    # ------------------------------------------------------------ internals
    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request.get(host)
        if last is not None:
            remaining = self.delay - (time.monotonic() - last)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request[host] = time.monotonic()

    def _cache_path(self, key: str) -> Path:
        return CACHE_DIR / (hashlib.sha1(key.encode()).hexdigest() + ".cache")

    def _cached(self, key: str) -> str | None:
        if not self.use_cache:
            return None
        p = self._cache_path(key)
        if p.exists() and time.time() - p.stat().st_mtime < self.cache_ttl:
            return p.read_text(encoding="utf-8")
        return None

    def _store(self, key: str, text: str) -> None:
        if not self.use_cache:
            return
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cache_path(key).write_text(text, encoding="utf-8")

    # ------------------------------------------------------------ public API
    def request(self, method: str, url: str, *, params=None, json_body=None, headers=None, timeout=30,
                validate=None) -> str:
        """Fetch a URL (cached). `validate(text)` may raise; invalid responses are never cached."""
        key = json.dumps([method, url, params, json_body], sort_keys=True)
        cached = self._cached(key)
        if cached is not None:
            log.debug("cache hit %s", url)
            return cached
        self._wait(url)
        log.info("%s %s", method, url)
        resp = self.session.request(method, url, params=params, json=json_body, headers=headers, timeout=timeout)
        self.requests_made += 1
        for wait in (10, 30):
            if not (resp.ok and not resp.content):
                break
            # some sites intermittently answer with an empty body (Melkweg from CI, ~50%) → retry twice
            log.warning("empty response from %s, retrying in %d s", url, wait)
            time.sleep(wait)
            resp = self.session.request(method, url, params=params, json=json_body, headers=headers, timeout=timeout)
            self.requests_made += 1
        resp.raise_for_status()
        text = resp.text
        if any(marker in text[:3000] for marker in BOT_PAGE_MARKERS):
            raise BlockedError(f"{urlparse(url).netloc} served a bot-check page")
        if validate:
            validate(text)
        self._store(key, text)
        return text

    def get_text(self, url: str, **kw) -> str:
        return self.request("GET", url, **kw)

    def get_json(self, url: str, **kw):
        return json.loads(self.request("GET", url, validate=json.loads, **kw))

    def post_json(self, url: str, body: dict, **kw):
        return json.loads(self.request("POST", url, json_body=body, validate=json.loads, **kw))

    def render(self, url: str, *, scroll: int = 0, wait_selector: str | None = None,
               click_more: str | None = None, max_clicks: int = 10) -> str:
        """Load a page in headless Chromium and return the final HTML.

        scroll: number of times to scroll to the bottom (for infinite scroll)
        click_more: CSS selector of a "load more" button to click until it disappears
        """
        key = json.dumps(["RENDER", url, scroll, wait_selector, click_more])
        cached = self._cached(key)
        if cached is not None:
            return cached
        self._wait(url)
        log.info("RENDER %s", url)
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch()
        page = self._browser.new_page(user_agent=BROWSER_UA, locale="nl-NL")
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            if wait_selector:
                page.wait_for_selector(wait_selector, timeout=30000)
            for _ in range(scroll):
                page.mouse.wheel(0, 20000)
                page.wait_for_timeout(1500)
            if click_more:
                for _ in range(max_clicks):
                    btn = page.query_selector(click_more)
                    if not btn or not btn.is_visible():
                        break
                    btn.click()
                    page.wait_for_timeout(2000)
            text = page.content()
        finally:
            page.close()
        self.requests_made += 1
        self._store(key, text)
        return text

    def close(self) -> None:
        if self._browser:
            self._browser.close()
            self._pw.stop()
            self._browser = None
