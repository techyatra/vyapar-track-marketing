"""Publishes every row in content_queue with status='approved':
  - linkedin, facebook   -> posted immediately via their APIs
  - instagram            -> a branded graphic is generated, committed+pushed
                             to this repo (so it has a public raw.githubusercontent.com
                             URL), then posted via the Graph API's two-step publish
  - x                    -> never auto-posted (no paid API tier); just flipped to
                             'manual_x_ready' so the dashboard shows copy-paste text
  - youtube               -> full render (voice + Playwright/ffmpeg + thumbnail)
                             happens HERE, after approval, then uploaded

    python main_publish.py             # all approved rows
    python main_publish.py --dry-run   # do everything except the real API calls
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import graphic_generator, linkedin_poster, meta_poster, x_formatter  # noqa: E402
from engine.supabase_client import get_client  # noqa: E402
from engine.youtube import scene_renderer, thumbnail_generator, voice_generator, youtube_uploader  # noqa: E402

ROOT = Path(__file__).resolve().parent
GENERATED_DIR = ROOT / "docs" / "generated"
RAW_BASE = "https://raw.githubusercontent.com/techyatra/vyapar-track-marketing/main"


def _load_settings() -> dict:
    path = ROOT / "config" / "settings.json"
    if not path.is_file():
        path = ROOT / "config" / "settings.example.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def _commit_and_push(relative_path: Path, message: str) -> None:
    _git("config", "user.name", "github-actions[bot]")
    _git("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    _git("add", str(relative_path))
    diff = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=ROOT)
    if diff.returncode == 0:
        return  # nothing changed
    _git("commit", "-m", message)
    _git("push")


def publish_linkedin(row: dict, *, dry_run: bool) -> dict:
    text = "\n\n".join(
        part for part in (row["hook"], row["body"], row["cta"], " ".join(row.get("hashtags") or [])) if part
    )
    post_id = linkedin_poster.publish_text_post(
        access_token=os.environ["LINKEDIN_ACCESS_TOKEN"],
        author_urn=os.environ.get("LINKEDIN_ORG_URN") or os.environ["LINKEDIN_PERSON_URN"],
        text=text,
        dry_run=dry_run,
    )
    return {"platform_post_id": post_id, "platform_post_url": None}


def publish_facebook(row: dict, *, dry_run: bool) -> dict:
    text = "\n\n".join(part for part in (row["hook"], row["body"], row["cta"]) if part)
    post_id = meta_poster.publish_facebook_text_post(
        access_token=os.environ["META_PAGE_ACCESS_TOKEN"],
        page_id=os.environ["META_FB_PAGE_ID"],
        message=text,
        dry_run=dry_run,
    )
    url = f"https://facebook.com/{post_id}" if post_id else None
    return {"platform_post_id": post_id, "platform_post_url": url}


def publish_instagram(row: dict, *, dry_run: bool) -> dict:
    image_path = GENERATED_DIR / f"{row['id']}.png"
    graphic_generator.generate_graphic(hook=row["hook"], out_path=image_path)

    if dry_run:
        print(f"[dry-run] would commit+push {image_path} and publish IG post {row['id']}")
        return {"platform_post_id": None, "platform_post_url": None}

    _commit_and_push(image_path.relative_to(ROOT), f"chore: generated IG graphic for {row['id']}")
    # raw.githubusercontent.com takes a few seconds to reflect a fresh push.
    time.sleep(8)
    image_url = f"{RAW_BASE}/docs/generated/{row['id']}.png"

    caption = "\n\n".join(part for part in (row["hook"], row["body"], row["cta"], " ".join(row.get("hashtags") or [])) if part)
    post_id = meta_poster.publish_instagram_image_post(
        access_token=os.environ["META_PAGE_ACCESS_TOKEN"],
        ig_user_id=os.environ["META_IG_USER_ID"],
        image_url=image_url,
        caption=caption,
        dry_run=dry_run,
    )
    return {"platform_post_id": post_id, "platform_post_url": None}


def publish_youtube(row: dict, *, dry_run: bool) -> dict:
    settings = _load_settings()
    scenes = json.loads(row["body"])

    run_id = row["id"]
    work_dir = ROOT / "output" / run_id
    voice = settings["youtube"]["voice"]["en"]
    voice_generator.generate_all_scene_audio(scenes=scenes, voice=voice, work_dir=work_dir / "audio")

    final_mp4 = scene_renderer.render_video(
        scenes=scenes,
        work_dir=work_dir / "render",
        out_mp4=work_dir / "final.mp4",
        fps=settings["youtube"]["fps"],
        resolution=(settings["youtube"]["resolution"]["width"], settings["youtube"]["resolution"]["height"]),
    )
    thumb_paths = thumbnail_generator.generate_thumbnails(
        variant_texts=[row["yt_thumbnail_text"]], out_dir=work_dir / "thumbnails"
    )

    video_id = youtube_uploader.upload_video(
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        video_path=final_mp4,
        thumbnail_path=thumb_paths[0] if thumb_paths else None,
        title=row["yt_title"],
        description=row["yt_description"],
        tags=row.get("yt_tags"),
        category_id=settings["youtube"]["category_id"],
        privacy_status=settings["youtube"]["privacy_status_on_upload"],
        dry_run=dry_run,
    )
    url = f"https://youtube.com/watch?v={video_id}" if video_id else None
    return {"platform_post_id": video_id, "platform_post_url": url}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = get_client()
    rows = db.table("content_queue").select("*").eq("status", "approved").execute().data

    for row in rows:
        platform = row["platform"]
        print(f"[publish] {platform} id={row['id']} topic={row['topic']!r}")
        try:
            if platform == "linkedin":
                result = publish_linkedin(row, dry_run=args.dry_run)
            elif platform == "facebook":
                result = publish_facebook(row, dry_run=args.dry_run)
            elif platform == "instagram":
                result = publish_instagram(row, dry_run=args.dry_run)
            elif platform == "youtube":
                result = publish_youtube(row, dry_run=args.dry_run)
            elif platform == "x":
                formatted = x_formatter.validate_and_format(hook=row["hook"], body=row["body"], cta=row["cta"])
                db.table("content_queue").update(
                    {"status": "manual_x_ready", "visual_direction": formatted["copy_paste_text"]}
                ).eq("id", row["id"]).execute()
                print(f"  -> flagged manual_x_ready ({formatted['mode']})")
                continue
            else:
                raise ValueError(f"Unknown platform {platform!r}")

            if args.dry_run:
                continue

            db.table("content_queue").update(
                {
                    "status": "published",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "platform_post_id": result["platform_post_id"],
                    "platform_post_url": result["platform_post_url"],
                }
            ).eq("id", row["id"]).execute()
            print(f"  -> published: {result}")

        except Exception as exc:  # noqa: BLE001 — one bad row must not block the rest of the run
            print(f"  -> FAILED: {exc}")
            if not args.dry_run:
                db.table("content_queue").update({"status": "failed", "reviewer_note": str(exc)[:500]}).eq(
                    "id", row["id"]
                ).execute()


if __name__ == "__main__":
    main()
