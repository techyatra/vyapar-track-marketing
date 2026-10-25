"""Renders scenes to a final MP4: HTML/CSS/JS scenes -> Playwright frame capture -> ffmpeg assembly.

This is the "treat the edit as code" technique: templates/scene.html exposes a
`renderFrame(t)` JS function; we drive it frame-by-frame from Python and
screenshot each frame, so renders never drift from what the code describes.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "scene.html"
TAIL_PAD_SECONDS = 0.35


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")


def _render_scene_frames(
    page: Any, scene: dict[str, Any], frames_dir: Path, fps: int
) -> int:
    frames_dir.mkdir(parents=True, exist_ok=True)
    page.evaluate("setScene", scene)
    duration = float(scene["duration_seconds"]) + TAIL_PAD_SECONDS
    num_frames = max(1, math.ceil(duration * fps))
    for i in range(num_frames):
        t = i / fps
        page.evaluate(f"renderFrame({t})")
        page.screenshot(path=str(frames_dir / f"frame_{i:05d}.png"))
    return num_frames


def _assemble_scene_video(
    *, frames_dir: Path, audio_path: Path, fps: int, out_mp4: Path
) -> None:
    _run([
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%05d.png"),
        "-i", str(audio_path),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(out_mp4),
    ])


def _concat_videos(scene_videos: list[Path], out_mp4: Path, work_dir: Path) -> None:
    concat_list = work_dir / "concat_list.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in scene_videos), encoding="utf-8"
    )
    _run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(out_mp4),
    ])


def render_video(
    *,
    scenes: list[dict[str, Any]],
    work_dir: Path,
    out_mp4: Path,
    fps: int = 30,
    resolution: tuple[int, int] = (1080, 1920),
) -> Path:
    """`scenes` must already have `audio_path`, `duration_seconds`, `words` set
    (see engine.voice_generator.generate_all_scene_audio)."""
    from playwright.sync_api import sync_playwright

    work_dir.mkdir(parents=True, exist_ok=True)
    scene_videos: list[Path] = []

    # PLAYWRIGHT_CHROMIUM_PATH lets a local dev shell reuse a pre-installed
    # browser whose revision doesn't match this pip package (e.g. a shared
    # sandbox image). Leave unset in CI/GitHub Actions: `playwright install
    # chromium` there installs the exact matching revision and default
    # discovery just works.
    launch_kwargs: dict[str, Any] = {}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_PATH"):
        launch_kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_PATH"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": resolution[0], "height": resolution[1]})
        page.goto(TEMPLATE_PATH.as_uri())
        page.wait_for_function("window.renderFrame !== undefined")

        for i, scene in enumerate(scenes):
            scene_dir = work_dir / f"scene_{i:02d}"
            frames_dir = scene_dir / "frames"
            _render_scene_frames(page, scene, frames_dir, fps)
            scene_mp4 = scene_dir / "scene.mp4"
            _assemble_scene_video(
                frames_dir=frames_dir,
                audio_path=Path(scene["audio_path"]),
                fps=fps,
                out_mp4=scene_mp4,
            )
            scene_videos.append(scene_mp4)

        browser.close()

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    _concat_videos(scene_videos, out_mp4, work_dir)
    return out_mp4


if __name__ == "__main__":
    # Smoke test: renders a 2-scene video from placeholder data, no network needed
    # if silent placeholder audio files are supplied externally. See scripts/smoke_test.py.
    import sys

    scenes_path = Path(sys.argv[1])
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    out = render_video(
        scenes=scenes,
        work_dir=Path("output/_render_work"),
        out_mp4=Path("output/_smoke_test.mp4"),
    )
    print(f"Rendered: {out}")
