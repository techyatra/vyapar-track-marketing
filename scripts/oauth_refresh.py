"""Refreshes LinkedIn and Meta access tokens before they expire, prints the
new values as GitHub Actions output lines so the workflow can rotate the
GitHub Secrets (same pattern as techyatra/Linkedin-Automator's
oauth-refresh.yml). YouTube's refresh token doesn't need rotating — Google
refreshes the short-lived access token on every use automatically; it only
needs re-minting (via scripts/youtube_oauth_setup.py) if the pipeline goes
quiet for 7+ days while the OAuth consent screen is still in "Testing" mode.

    python scripts/oauth_refresh.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import linkedin_poster, meta_poster  # noqa: E402


def refresh_linkedin() -> None:
    refresh_token = os.environ.get("LINKEDIN_REFRESH_TOKEN")
    if not refresh_token:
        print("No LINKEDIN_REFRESH_TOKEN set — LinkedIn app is likely not approved for refresh "
              "tokens; re-run scripts/linkedin_oauth_setup.py before the 60-day access token expires.")
        return

    tokens = linkedin_poster.refresh_access_token(
        client_id=os.environ["LINKEDIN_CLIENT_ID"],
        client_secret=os.environ["LINKEDIN_CLIENT_SECRET"],
        refresh_token=refresh_token,
    )
    print(f"##NEW_LINKEDIN_ACCESS_TOKEN={tokens['access_token']}")
    if tokens.get("refresh_token"):
        print(f"##NEW_LINKEDIN_REFRESH_TOKEN={tokens['refresh_token']}")


def refresh_meta() -> None:
    page_token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    app_id = os.environ.get("META_APP_ID")
    app_secret = os.environ.get("META_APP_SECRET")
    if not (page_token and app_id and app_secret):
        print("Meta env vars not fully set — skipping Meta token refresh.")
        return

    result = meta_poster.exchange_for_long_lived_token(
        app_id=app_id, app_secret=app_secret, short_lived_token=page_token
    )
    print(f"##NEW_META_PAGE_ACCESS_TOKEN={result['access_token']}")


def main() -> None:
    refresh_linkedin()
    refresh_meta()


if __name__ == "__main__":
    main()
