"""Fetch new Instagram posts of the accounts in instagram/accounts.json via the official Graph API
('Business Discovery': public posts of business/creator accounts, read with the owner's own token).

Run by .github/workflows/instagram.yml with secrets IG_TOKEN and IG_USER_ID. Writes into an inbox
directory (the `instagram-inbox` branch):
  seen.json                   ids already fetched
  pending/<username>__<id>.json   caption, timestamp, permalink, venue
  pending/<username>__<id>_<n>.jpg  up to 3 images, max 1000 px (posters!)
The weekly Claude task reads pending/, extracts events into instagram/events.json and deletes them.

Usage: python instagram/fetch.py <inbox_dir>
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image

GRAPH = "https://graph.facebook.com/" + (os.environ.get("GRAPH_VERSION", "").strip("/") + "/" if os.environ.get("GRAPH_VERSION") else "")
MAX_AGE_DAYS = 21
MAX_IMAGES = 3
HERE = Path(__file__).resolve().parent
MEDIA_FIELDS = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"


def discover(session, ig_user_id: str, token: str, username: str) -> list[dict]:
    for children in (True, False):  # nested children are not available on every API version
        media = MEDIA_FIELDS + (",children{media_type,media_url,thumbnail_url}" if children else "")
        fields = f"business_discovery.username({username}){{username,media.limit(15){{{media}}}}}"
        r = session.get(GRAPH + ig_user_id, params={"fields": fields, "access_token": token}, timeout=30)
        if r.ok:
            return r.json()["business_discovery"]["media"]["data"]
        err = r.json().get("error", {}) if r.headers.get("content-type", "").startswith(("application/json", "text/javascript")) else {}
        if children and "children" in str(err.get("message", "")):
            continue
        raise RuntimeError(f"{username}: HTTP {r.status_code} {err.get('message') or r.text[:200]}")
    return []


def image_urls(post: dict) -> list[str]:
    items = post.get("children", {}).get("data") or [post]
    urls = [(c.get("thumbnail_url") if c.get("media_type") == "VIDEO" else c.get("media_url")) or c.get("thumbnail_url")
            for c in items]
    return [u for u in urls if u][:MAX_IMAGES]


def save_image(session, url: str, path: Path) -> None:
    img = Image.open(io.BytesIO(session.get(url, timeout=30).content)).convert("RGB")
    img.thumbnail((1000, 1000))
    img.save(path, "JPEG", quality=82)


def main(inbox: Path) -> int:
    token, ig_user_id = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
    accounts = json.loads((HERE / "accounts.json").read_text())["accounts"]
    seen_file = inbox / "seen.json"
    seen = set(json.loads(seen_file.read_text())) if seen_file.exists() else set()
    pending = inbox / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    session = requests.Session()
    session.headers["User-Agent"] = "AmsterdamAgendaBot/1.0 (personal event calendar; weekly run)"
    new, failed = 0, []
    for acc in accounts:
        user = acc["username"].lstrip("@")
        try:
            posts = discover(session, ig_user_id, token, user)
        except Exception as exc:  # one account failing must not stop the rest
            print(f"FAILED {user}: {exc}")
            failed.append(user)
            continue
        for post in posts:
            ts = datetime.strptime(post["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            if post["id"] in seen or ts < cutoff:
                continue
            stem = f"{user}__{post['id']}"
            images = []
            for n, url in enumerate(image_urls(post)):
                try:
                    save_image(session, url, pending / f"{stem}_{n}.jpg")
                    images.append(f"{stem}_{n}.jpg")
                except Exception as exc:
                    print(f"image {stem}_{n} failed: {exc}")
            (pending / f"{stem}.json").write_text(json.dumps({
                "username": user, "venue": acc.get("venue") or user, "id": post["id"],
                "timestamp": post["timestamp"], "permalink": post.get("permalink"),
                "caption": post.get("caption") or "", "images": images}, ensure_ascii=False, indent=1))
            seen.add(post["id"])
            new += 1
        time.sleep(1)
    seen_file.write_text(json.dumps(sorted(seen)))
    print(f"{new} new posts from {len(accounts) - len(failed)}/{len(accounts)} accounts"
          + (f"; FAILED: {', '.join(failed)}" if failed else ""))
    return 1 if failed and len(failed) == len(accounts) else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "inbox")))
