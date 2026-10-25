"""Local smoke test for the render pipeline: no network calls (no Gemini, no
edge-tts, no Supabase). Generates silent placeholder audio with ffmpeg and a
hand-written VyaparTrack sample script, then runs the real scene_renderer
against it. Verifies Playwright + ffmpeg actually produce a playable MP4
end to end, same approach as techyatra/youtube-automator's smoke test.

    python scripts/smoke_test_render.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.youtube.scene_renderer import render_video  # noqa: E402

SAMPLE_SCENES = [
    {
        "type": "title_card",
        "narration": "Still reconciling three firms' books by hand before every GST return?",
        "visual": {"title": "Three firms. One midnight.", "subtitle": "There's a faster way."},
        "duration_seconds": 3.5,
        "words": [
            {"text": "Still", "start": 0.0, "end": 0.3},
            {"text": "reconciling", "start": 0.3, "end": 0.9},
            {"text": "three", "start": 0.9, "end": 1.2},
            {"text": "firms?", "start": 1.2, "end": 1.7},
        ],
    },
    {
        "type": "feature_card",
        "narration": "VyaparTrack switches between every firm's books instantly, from one login.",
        "visual": {"feature": "Multi-firm, one login", "benefit": "Switch firms instantly. Books, stock, and bills stay isolated per firm."},
        "duration_seconds": 4.0,
        "words": [],
    },
    {
        "type": "comparison",
        "narration": "Tally plus Excel plus WhatsApp versus one screen that already knows your GST split.",
        "visual": {
            "left_label": "BEFORE",
            "left_text": "Tally + Excel + WhatsApp, three sets of books",
            "right_label": "WITH VYAPARTRACK",
            "right_text": "One screen, GST split done automatically",
        },
        "duration_seconds": 4.0,
        "words": [],
    },
    {
        "type": "outro_card",
        "narration": "Try VyaparTrack free for six months. No card required.",
        "visual": {"title": "Free for 6 months", "subtitle": "No card required"},
        "duration_seconds": 2.5,
        "words": [],
    },
]


def make_silent_audio(out_mp3: Path, seconds: float) -> None:
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(seconds),
            "-q:a", "9",
            str(out_mp3),
        ],
        check=True, capture_output=True,
    )


def main() -> None:
    work_dir = Path("output/_smoke_work")
    for i, scene in enumerate(SAMPLE_SCENES):
        audio_path = work_dir / f"placeholder_{i:02d}.mp3"
        make_silent_audio(audio_path, scene["duration_seconds"])
        scene["audio_path"] = str(audio_path)

    out = render_video(
        scenes=SAMPLE_SCENES,
        work_dir=work_dir,
        out_mp4=Path("output/_smoke_test.mp4"),
    )
    print(f"OK: rendered {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
