"""Instagram + Facebook posting via the Meta Graph API.

CODE IS READY; THIS CANNOT RUN until you complete:
1. An Instagram **Business or Creator** account, linked to a Facebook Page.
2. A Meta for Developers app in Live mode with the `instagram_content_publish`
   and `pages_manage_posts` permissions approved by App Review (Meta's
   manual review, not instant — budget 1-2 weeks, see README).
See README.md "Meta (Instagram/Facebook) setup" for the exact steps.

Flow for Instagram (Graph API's two-step publish):
  1. POST /{ig_user_id}/media       -> create a media container (image/video + caption)
  2. POST /{ig_user_id}/media_publish -> publish that container
Facebook Page posts are a single call to /{page_id}/feed (text) or
/{page_id}/photos (image).
"""

from __future__ import annotations

import time

import requests

GRAPH_BASE = "https://graph.facebook.com/v21.0"


def publish_instagram_image_post(
    *, access_token: str, ig_user_id: str, image_url: str, caption: str, dry_run: bool = False
) -> str | None:
    """`image_url` must be a publicly reachable HTTPS URL (Meta fetches it
    server-side) — e.g. an image committed to this repo and served via
    GitHub Pages/raw.githubusercontent.com, or uploaded to any public host."""
    if dry_run:
        print(f"[dry-run] would publish IG post: {caption[:120]!r} image={image_url}")
        return None

    create = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    create.raise_for_status()
    container_id = create.json()["id"]

    # Media containers process asynchronously; poll briefly before publishing.
    for _ in range(10):
        status = requests.get(
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=15,
        ).json()
        if status.get("status_code") == "FINISHED":
            break
        time.sleep(3)

    publish = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    publish.raise_for_status()
    return publish.json()["id"]


def publish_facebook_text_post(*, access_token: str, page_id: str, message: str, dry_run: bool = False) -> str | None:
    if dry_run:
        print(f"[dry-run] would post to FB Page {page_id}: {message[:120]!r}")
        return None

    resp = requests.post(
        f"{GRAPH_BASE}/{page_id}/feed",
        data={"message": message, "access_token": access_token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def exchange_for_long_lived_token(*, app_id: str, app_secret: str, short_lived_token: str) -> dict:
    """Short-lived user tokens expire in ~1-2 hours; exchange once for a
    long-lived (60-day) token, then re-exchange it before expiry (see
    oauth-refresh.yml) — Page access tokens derived from a long-lived user
    token effectively never expire as long as this runs periodically."""
    resp = requests.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_lived_token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
