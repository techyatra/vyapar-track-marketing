"""Generates a YouTube Short SCRIPT (no rendering yet) and queues it for
approval. Rendering (voice + Playwright/ffmpeg + thumbnail) is deliberately
deferred to main_publish.py, after a human approves the script — rendering
is the expensive step, and there's no reason to pay for it on a script that
gets rejected.

    python main_youtube_short.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import content_writer, safety_check, topic_picker  # noqa: E402
from engine.supabase_client import get_client  # noqa: E402


def main() -> None:
    api_key = os.environ["GEMINI_API_KEY"]
    db = get_client()

    recent_rows = (
        db.table("content_queue")
        .select("topic")
        .eq("platform", "youtube")
        .order("created_at", desc=True)
        .limit(15)
        .execute()
    )
    recent_topics = [r["topic"] for r in recent_rows.data]

    topic_data = topic_picker.pick_topic(platform="youtube", recent_topics=recent_topics, api_key=api_key)
    script = content_writer.write_post(
        platform="youtube",
        pillar_name=topic_data["pillar_name"],
        topic=topic_data["topic"],
        angle=topic_data["angle"],
        api_key=api_key,
    )
    safety = safety_check.check_youtube_script_safety(
        title=script["yt_title"], description=script["yt_description"], scenes=script["yt_script"], api_key=api_key
    )

    row = {
        "platform": "youtube",
        "pillar_id": topic_data["pillar_id"],
        "topic": topic_data["topic"],
        "yt_title": script["yt_title"],
        "yt_description": script["yt_description"],
        "yt_tags": script["yt_tags"],
        "yt_thumbnail_text": script["yt_thumbnail_text"],
        "best_time_ist": script.get("best_time_ist"),
        "body": json.dumps(script["yt_script"]),  # the scene script, re-parsed at publish time
        "safety_safe": safety["safe"],
        "safety_concerns": safety["concerns"],
        "safety_reasoning": safety["reasoning"],
        "status": "pending_approval",
    }
    inserted = db.table("content_queue").insert(row).execute()
    print(f"[queued] youtube: {row['topic']} (safe={row['safety_safe']}) id={inserted.data[0]['id']}")


if __name__ == "__main__":
    main()
