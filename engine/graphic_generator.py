"""Generates a single branded hook/stat graphic for Instagram + Facebook
posts, via the same HTML-as-code + Playwright-screenshot technique as the
YouTube thumbnail generator. No image-gen API, no designer required.

Scope honesty: this produces ONE static graphic per post, not a real
carousel (4-6 slides) or a reel (video). The brief's "carousel/reel" visual
directions are a backlog item (richer asset generation) — for now, every
Instagram/Facebook post gets this single graphic attached, which is enough
to satisfy Instagram's Graph API requirement that every post carry media
(Instagram does not allow text-only posts; Facebook does, see
engine/meta_poster.publish_facebook_text_post for the text-only path).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "graphic.html"

# Instagram feed: 4:5 portrait is the safest aspect ratio for both feed and
# profile grid rendering.
DEFAULT_SIZE = (1080, 1350)


def generate_graphic(*, hook: str, stat: str = "", label: str = "", out_path: Path, size: tuple[int, int] = DEFAULT_SIZE) -> Path:
    from playwright.sync_api import sync_playwright

    out_path.parent.mkdir(parents=True, exist_ok=True)
    launch_kwargs: dict[str, Any] = {}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_PATH"):
        launch_kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_PATH"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        page.goto(TEMPLATE_PATH.as_uri())
        page.wait_for_function("window.setGraphic !== undefined")
        page.evaluate("setGraphic", {"hook": hook, "stat": stat, "label": label})
        page.screenshot(path=str(out_path))
        browser.close()
    return out_path
