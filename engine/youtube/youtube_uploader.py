"""Unattended YouTube Data API v3 uploads, driven entirely by a refresh token
(no browser, no local server — safe to run in GitHub Actions).

The refresh token is minted ONCE, interactively, on your own machine via
`scripts/youtube_oauth_setup.py`, then stored as a GitHub Secret. Google
OAuth refresh tokens for apps in "Testing" publish status expire after 7
days of inactivity but do NOT expire on a fixed schedule like LinkedIn's —
as long as this pipeline runs at least once a week, it keeps working. Set
your OAuth consent screen to "In production" (see README) to remove even
that limit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
)


def _build_credentials(*, client_id: str, client_secret: str, refresh_token: str) -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=list(SCOPES),
    )
    creds.refresh(Request())
    return creds


def upload_video(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    video_path: Path,
    thumbnail_path: Path | None,
    title: str,
    description: str,
    tags: Iterable[str] | None,
    category_id: str = "28",
    privacy_status: str = "public",
    dry_run: bool = False,
) -> str | None:
    if dry_run:
        print(f"[dry-run] would upload `{video_path}` titled `{title[:120]}` (privacy={privacy_status})")
        return None

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = _build_credentials(
        client_id=client_id, client_secret=client_secret, refresh_token=refresh_token
    )
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body: dict[str, Any] = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": list(tags or ()),
            "categoryId": str(category_id),
        },
        "status": {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False},
    }
    response = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
    ).execute()
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError(f"YouTube upload returned no video id: {response}")

    if thumbnail_path and thumbnail_path.is_file():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path)),
        ).execute()

    return str(video_id)
