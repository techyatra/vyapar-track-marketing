"""Instagram + Facebook posting via the Meta Graph API.

CODE IS READY; THIS CANNOT RUN until you complete:
1. An Instagram **Business or Creator** account, linked to a Facebook Page.
2. A Meta for Developers app in Live mode with the `instagram_content_publish`
   and `pages_manage_posts` permissions approved by App Review (Meta's
   manual review, not instant — budget 1-2 weeks, see README).
See README.md "Meta (Instagram/Facebook) setup" for the exact steps.

Flow for Instagram:
  Single image: POST /media (image_url+caption) -> wait -> POST /media_publish
  Carousel:     POST /media (image_url, is_carousel_item=true) per slide
                -> POST /media (media_type=CAROUSEL, children=[...], caption)
                -> wait -> POST /media_publish
  Reel:         POST /media (media_type=REELS, video_url, caption) -> wait
                (longer — video processing) -> POST /media_publish
Facebook Page posts are a single call to /{page_id}/feed (text) or
/{page_id}/photos (image).
"""

from __future__ import annotations

import time

import requests

GRAPH_BASE = "https://graph.facebook.com/v21.0"


def _wait_for_container(*, container_id: str, access_token: str, max_wait_seconds: int = 60, poll_seconds: int = 5) -> None:
    """Media containers (image, carousel item, or video) process
    asynchronously server-side before they can be published. Reels take
    noticeably longer than images — callers pass a larger max_wait_seconds
    for video."""
    waited = 0
    while waited < max_wait_seconds:
        status = requests.get(
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=15,
        ).json()
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Media container {container_id} failed processing: {status}")
        time.sleep(poll_seconds)
        waited += poll_seconds


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
    _wait_for_container(container_id=container_id, access_token=access_token)

    publish = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    publish.raise_for_status()
    return publish.json()["id"]


def publish_instagram_carousel(
    *, access_token: str, ig_user_id: str, image_urls: list[str], caption: str, dry_run: bool = False
) -> str | None:
    """`image_urls` are the already-committed+pushed slide images, in the
    publicly-reachable raw.githubusercontent.com form, in display order."""
    if dry_run:
        print(f"[dry-run] would publish IG carousel ({len(image_urls)} slides): {caption[:120]!r}")
        return None
    if not 2 <= len(image_urls) <= 10:
        raise ValueError(f"Instagram carousels need 2-10 slides, got {len(image_urls)}")

    child_ids = []
    for url in image_urls:
        create = requests.post(
            f"{GRAPH_BASE}/{ig_user_id}/media",
            data={"image_url": url, "is_carousel_item": "true", "access_token": access_token},
            timeout=30,
        )
        create.raise_for_status()
        child_id = create.json()["id"]
        _wait_for_container(container_id=child_id, access_token=access_token)
        child_ids.append(child_id)

    create_parent = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    create_parent.raise_for_status()
    parent_id = create_parent.json()["id"]
    _wait_for_container(container_id=parent_id, access_token=access_token)

    publish = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": parent_id, "access_token": access_token},
        timeout=30,
    )
    publish.raise_for_status()
    return publish.json()["id"]


def publish_instagram_reel(
    *, access_token: str, ig_user_id: str, video_url: str, caption: str, dry_run: bool = False
) -> str | None:
    """`video_url` must be a publicly reachable HTTPS URL to an MP4 (same
    commit-and-push-to-this-repo approach as the image/carousel paths).
    Video containers take noticeably longer to process than images."""
    if dry_run:
        print(f"[dry-run] would publish IG reel: {caption[:120]!r} video={video_url}")
        return None

    create = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={"media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    create.raise_for_status()
    container_id = create.json()["id"]
    _wait_for_container(container_id=container_id, access_token=access_token, max_wait_seconds=300, poll_seconds=10)

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
