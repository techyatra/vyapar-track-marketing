"""Pulls engagement metrics for recently-published posts and writes them to
post_analytics. Best-effort: a platform API error for one row logs and
continues rather than failing the whole run.

    python scripts/fetch_analytics.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.supabase_client import get_client  # noqa: E402


def fetch_linkedin_metrics(post_id: str, access_token: str) -> dict:
    encoded = requests.utils.quote(post_id, safe="")
    resp = requests.get(
        f"https://api.linkedin.com/v2/socialActions/{encoded}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "likes": data.get("likesSummary", {}).get("totalLikes"),
        "comments": data.get("commentsSummary", {}).get("totalComments"),
    }


def fetch_meta_metrics(post_id: str, access_token: str) -> dict:
    resp = requests.get(
        f"https://graph.facebook.com/v21.0/{post_id}/insights",
        params={"metric": "post_impressions,post_engaged_users", "access_token": access_token},
        timeout=15,
    )
    resp.raise_for_status()
    values = {d["name"]: d["values"][0]["value"] for d in resp.json().get("data", [])}
    return {"impressions": values.get("post_impressions"), "clicks": values.get("post_engaged_users")}


def main() -> None:
    db = get_client()
    rows = (
        db.table("content_queue")
        .select("id, platform, platform_post_id")
        .eq("status", "published")
        .not_.is_("platform_post_id", "null")
        .execute()
        .data
    )

    for row in rows:
        try:
            if row["platform"] == "linkedin":
                metrics = fetch_linkedin_metrics(row["platform_post_id"], os.environ["LINKEDIN_ACCESS_TOKEN"])
            elif row["platform"] in ("facebook", "instagram"):
                metrics = fetch_meta_metrics(row["platform_post_id"], os.environ["META_PAGE_ACCESS_TOKEN"])
            else:
                continue  # YouTube analytics need a separate Data API call; X has no API access

            db.table("post_analytics").insert(
                {"content_queue_id": row["id"], "platform": row["platform"], **metrics}
            ).execute()
            print(f"[analytics] {row['platform']} {row['id']}: {metrics}")
        except Exception as exc:  # noqa: BLE001
            print(f"[analytics] FAILED for {row['id']}: {exc}")


if __name__ == "__main__":
    main()
