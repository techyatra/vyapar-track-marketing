"""Free text-to-speech via edge-tts, with word-level timing for caption sync.

edge-tts is an unofficial wrapper around the free Microsoft Edge "Read Aloud"
service. No API key, no quota, no cost. Network access is required at
render time (GitHub Actions has it; a sandboxed dev shell may not).
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any


async def _synthesize(text: str, voice: str, out_mp3: Path) -> list[dict[str, Any]]:
    import edge_tts

    words: list[dict[str, Any]] = []
    communicate = edge_tts.Communicate(text, voice)
    with open(out_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append(
                    {
                        "text": chunk["text"],
                        "start": chunk["offset"] / 10_000_000,
                        "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                    }
                )
    return words


def _probe_duration_seconds(media_path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip())


def generate_scene_audio(*, text: str, voice: str, out_mp3: Path) -> dict[str, Any]:
    """Synthesizes `text` to `out_mp3`, returns {duration_seconds, words}."""
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    words = asyncio.run(_synthesize(text, voice, out_mp3))
    duration = _probe_duration_seconds(out_mp3)
    return {"duration_seconds": duration, "words": words}


def generate_all_scene_audio(
    *, scenes: list[dict[str, Any]], voice: str, work_dir: Path
) -> list[dict[str, Any]]:
    """Mutates and returns `scenes` with `audio_path`, `duration_seconds`, `words` added."""
    for i, scene in enumerate(scenes):
        out_mp3 = work_dir / f"scene_{i:02d}.mp3"
        timing = generate_scene_audio(text=scene["narration"], voice=voice, out_mp3=out_mp3)
        scene["audio_path"] = str(out_mp3)
        scene["duration_seconds"] = timing["duration_seconds"]
        scene["words"] = timing["words"]
    return scenes


if __name__ == "__main__":
    import sys

    text = sys.argv[1] if len(sys.argv) > 1 else "This is a test of the free voice engine."
    voice = sys.argv[2] if len(sys.argv) > 2 else "en-US-GuyNeural"
    result = generate_scene_audio(text=text, voice=voice, out_mp3=Path("output/_voice_test.mp3"))
    print(json.dumps(result, indent=2))
