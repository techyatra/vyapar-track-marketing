"""Generates thumbnail PNGs from a short punchy text, via the same
HTML-as-code technique as the video renderer. Free, no image-gen API.

Ported verbatim from techyatra/youtube-automator/engine/thumbnail_generator.py
— only templates/thumbnail.html (the visual) changed, not this driver.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "thumbnail.html"


def generate_thumbnails(*, variant_texts: list[str], out_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    launch_kwargs: dict[str, Any] = {}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_PATH"):
        launch_kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_PATH"]

    paths: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(TEMPLATE_PATH.as_uri())
        page.wait_for_function("window.setThumbnail !== undefined")
        for i, text in enumerate(variant_texts):
            page.evaluate("setThumbnail", {"text": text})
            out_path = out_dir / f"thumbnail_{i:02d}.png"
            page.screenshot(path=str(out_path))
            paths.append(out_path)
        browser.close()
    return paths
