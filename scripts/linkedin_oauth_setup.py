"""Run this ONCE, locally, to mint a LinkedIn access + refresh token pair.

LinkedIn's OAuth is authorization-code based (no out-of-the-box installed-app
flow like Google's), so this spins up a tiny local HTTP server to catch the
redirect, same idea as techyatra/Linkedin-Automator's web OAuth callback but
condensed into a standalone script.

Usage:
    python scripts/linkedin_oauth_setup.py <client_id> <client_secret>

Before running: in your LinkedIn Developer app, add this exact redirect URL
under Auth -> OAuth 2.0 settings:
    http://localhost:8765/callback
"""

from __future__ import annotations

import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = "w_member_social openid profile"

_received_code: list[str] = []


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server's required method name)
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            _received_code.append(params["code"][0])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Success - you can close this tab and return to the terminal.")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - silence default logging
        pass


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    client_id, client_secret = sys.argv[1], sys.argv[2]

    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": "vyapartrack-setup",
        }
    )
    print(f"Opening browser for LinkedIn authorization:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8765), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    thread.join(timeout=120)
    server.server_close()

    if not _received_code:
        print("Timed out waiting for the LinkedIn redirect. Try again.")
        sys.exit(1)

    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": _received_code[0],
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    tokens = resp.json()

    userinfo = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=15,
    ).json()

    print("\n--- Success. Add these as GitHub Secrets in your repo: ---\n")
    print(f"LINKEDIN_CLIENT_ID={client_id}")
    print(f"LINKEDIN_CLIENT_SECRET={client_secret}")
    print(f"LINKEDIN_ACCESS_TOKEN={tokens['access_token']}")
    print(f"LINKEDIN_REFRESH_TOKEN={tokens.get('refresh_token', '(none returned - see README)')}")
    print(f"LINKEDIN_PERSON_URN=urn:li:person:{userinfo['sub']}")
    print("\nDo not commit these anywhere. GitHub Secrets only.")
    print(
        "\nNote: LinkedIn only issues a refresh_token if your app has been "
        "approved for the 'Community Management API' refresh-token product. "
        "Without it, the access token lasts 60 days and you re-run this "
        "script every ~55 days — the oauth-refresh.yml workflow will remind you."
    )


if __name__ == "__main__":
    main()
