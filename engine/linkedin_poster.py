"""LinkedIn posting via the REST API, same endpoints/pattern as
techyatra/Linkedin-Automator's LinkedInClient.cs (ported to Python).

Needs an access token with the `w_member_social` scope (personal profile) or
posting rights on an organization page (`w_organization_social` + an org
URN). Token lifecycle (60-day access token, refresh token) is handled by
scripts/linkedin_oauth_setup.py once and oauth-refresh.yml monthly — this
module only POSTs with whatever access token it's given.
"""

from __future__ import annotations

import requests

API_BASE = "https://api.linkedin.com"
LINKEDIN_VERSION = "202405"


def _headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def publish_text_post(*, access_token: str, author_urn: str, text: str, dry_run: bool = False) -> str | None:
    """`author_urn` is `urn:li:person:{sub}` for a personal profile, or
    `urn:li:organization:{id}` for a company page."""
    if dry_run:
        print(f"[dry-run] would post to LinkedIn as {author_urn}: {text[:120]!r}")
        return None

    body = {
        "author": author_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    resp = requests.post(f"{API_BASE}/rest/posts", headers=_headers(access_token), json=body, timeout=30)
    resp.raise_for_status()
    post_id = resp.headers.get("x-restli-id") or resp.headers.get("X-RestLi-Id")
    if not post_id:
        raise RuntimeError(f"LinkedIn post succeeded but returned no id: {resp.headers}")
    return post_id


def fetch_person_urn(*, access_token: str) -> str:
    resp = requests.get(
        f"{API_BASE}/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    sub = resp.json()["sub"]
    return f"urn:li:person:{sub}"


def refresh_access_token(*, client_id: str, client_secret: str, refresh_token: str) -> dict:
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
