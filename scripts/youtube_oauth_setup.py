"""Run this ONCE, locally, on your own machine (not in CI) to mint a refresh
token for the unattended YouTube uploader. Opens a browser once for you to
sign in and grant access, then prints the refresh token to copy into GitHub
Secrets as YOUTUBE_REFRESH_TOKEN.

Ported verbatim from techyatra/youtube-automator/scripts/youtube_oauth_setup.py.

Usage:
    python scripts/youtube_oauth_setup.py path/to/client_secret.json
"""

from __future__ import annotations

import sys

SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
)


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], scopes=list(SCOPES))
    credentials = flow.run_local_server(port=8080)

    print("\n--- Success. Add these as GitHub Secrets in your repo: ---\n")
    print(f"YOUTUBE_CLIENT_ID={credentials.client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={credentials.client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")
    print("\nDo not commit these anywhere. GitHub Secrets only.")


if __name__ == "__main__":
    main()
