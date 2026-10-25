"""Reads config/posting_schedule.json, works out today's weekday in IST, and
generates one draft for each platform scheduled for today. Run once a day by
.github/workflows/daily-generate.yml.

    python scripts/run_scheduled_generation.py            # today's schedule
    python scripts/run_scheduled_generation.py --weekday 2 # force Wednesday (testing)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main_generate  # noqa: E402
import main_youtube_short  # noqa: E402
from engine.supabase_client import get_client  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekday", type=int, default=None, help="0=Mon..6=Sun, overrides today")
    args = parser.parse_args()

    schedule = json.loads((ROOT / "config" / "posting_schedule.json").read_text(encoding="utf-8"))
    weekday = args.weekday if args.weekday is not None else datetime.now(IST).weekday()
    platforms = schedule[str(weekday)]
    print(f"Weekday {weekday}: generating for {platforms}")

    api_key = os.environ["GEMINI_API_KEY"]
    db = get_client()

    for platform in platforms:
        if platform == "youtube":
            main_youtube_short.main()
        else:
            row = main_generate.generate_one(db, platform=platform, api_key=api_key)
            print(f"[queued] {platform}: {row['topic']} (safe={row['safety_safe']}) id={row['id']}")


if __name__ == "__main__":
    main()
