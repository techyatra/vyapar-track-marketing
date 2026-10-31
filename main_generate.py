"""Generates draft posts for LinkedIn, Instagram, Facebook and X, runs the
automated safety check, and writes them to the Supabase approval queue
(content_queue, status='pending_approval'). Nothing is posted here —
main_publish.py posts whatever a human has since approved.

    python main_generate.py                       # one post per text platform
    python main_generate.py --platform linkedin    # just one platform
    python main_generate.py --count 2              # N posts per platform
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import content_writer, safety_check, topic_picker  # noqa: E402
from engine.supabase_client import get_client  # noqa: E402

TEXT_PLATFORMS = ("linkedin", "instagram", "facebook", "x")


def _recent_topics(db, platform: str, limit: int = 20) -> list[str]:
    rows = (
        db.table("vt_content_queue")
        .select("topic")
        .eq("platform", platform)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [r["topic"] for r in rows.data]


def generate_one(db, *, platform: str, api_key: str) -> dict:
    recent = _recent_topics(db, platform)
    topic_data = topic_picker.pick_topic(platform=platform, recent_topics=recent, api_key=api_key)

    post = content_writer.write_post(
        platform=platform,
        pillar_name=topic_data["pillar_name"],
        topic=topic_data["topic"],
        angle=topic_data["angle"],
        api_key=api_key,
    )
    safety = safety_check.check_post_safety(hook=post["hook"], body=post["body"], cta=post["cta"], api_key=api_key)

    row = {
        "platform": platform,
        "pillar_id": topic_data["pillar_id"],
        "topic": topic_data["topic"],
        "hook": post["hook"],
        "body": post["body"],
        "cta": post["cta"],
        "hashtags": post["hashtags"],
        "visual_direction": post["visual_direction"],
        "alt_text": post["alt_text"],
        "best_time_ist": post["best_time_ist"],
        "safety_safe": safety["safe"],
        "safety_concerns": safety["concerns"],
        "safety_reasoning": safety["reasoning"],
        "status": "pending_approval",
    }

    if platform == "instagram":
        # Facebook posts stay text-only (publish_facebook_text_post) in this
        # engine, so visual_type/reel generation would be wasted work there.
        visual_type = content_writer.classify_visual_type(post["visual_direction"])
        row["visual_type"] = visual_type
        if visual_type == "reel":
            reel = content_writer.write_reel_script(
                pillar_name=topic_data["pillar_name"],
                topic=topic_data["topic"],
                angle=topic_data["angle"],
                caption_hook=post["hook"],
                caption_body=post["body"],
                api_key=api_key,
            )
            row["reel_script"] = reel["reel_script"]

    inserted = db.table("vt_content_queue").insert(row).execute()
    return inserted.data[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=TEXT_PLATFORMS, default=None)
    parser.add_argument("--count", type=int, default=1)
    args = parser.parse_args()

    api_key = os.environ["GEMINI_API_KEY"]
    db = get_client()
    platforms = [args.platform] if args.platform else TEXT_PLATFORMS

    results = []
    failures = []
    for platform in platforms:
        for _ in range(args.count):
            try:
                row = generate_one(db, platform=platform, api_key=api_key)
                print(f"[queued] {platform}: {row['topic']} (safe={row['safety_safe']}) id={row['id']}")
                results.append(row)
            except Exception as exc:  # noqa: BLE001 — one platform's failure must not block the rest
                print(f"[FAILED] {platform}: {exc}")
                failures.append({"platform": platform, "error": str(exc)})

    print(json.dumps({"queued": len(results), "failed": failures}, indent=2))
    if failures:
        sys.exit(1)  # surface in the Actions run, but only after every platform was attempted


if __name__ == "__main__":
    main()
