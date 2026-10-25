"""Renders a real Instagram/Facebook carousel (up to 10 slides) from
structured slide data, via the same HTML + Playwright screenshot technique
as the rest of the engine. This replaces the single-graphic fallback for
posts whose visual_direction calls for a carousel.

Slide dict shape (see templates/carousel_slide.html for the renderer):
    {"type": "title" | "bullets" | "stat" | "comparison" | "cta",
     "visual": {...fields for that type...}}
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "carousel_slide.html"

# Same 4:5 portrait used for the single-graphic generator — the safest
# aspect ratio across IG feed, profile grid, and carousel swipe view.
SLIDE_SIZE = (1080, 1350)
FOOTER_TEXT = "Free 6-month trial · No card required"


def generate_carousel(*, slides: list[dict[str, Any]], out_dir: Path, size: tuple[int, int] = SLIDE_SIZE) -> list[Path]:
    from playwright.sync_api import sync_playwright

    if not 2 <= len(slides) <= 10:
        raise ValueError(f"Instagram carousels need 2-10 slides, got {len(slides)}")

    out_dir.mkdir(parents=True, exist_ok=True)
    launch_kwargs: dict[str, Any] = {}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_PATH"):
        launch_kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_PATH"]

    paths: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        page.goto(TEMPLATE_PATH.as_uri())
        page.wait_for_function("window.setSlide !== undefined")

        for i, slide in enumerate(slides):
            payload = dict(slide)
            payload["page_label"] = f"{i + 1}/{len(slides)}"
            payload["footer"] = FOOTER_TEXT if i == len(slides) - 1 else ""
            page.evaluate("setSlide", payload)
            out_path = out_dir / f"slide_{i:02d}.png"
            page.screenshot(path=str(out_path))
            paths.append(out_path)

        browser.close()
    return paths


def build_slides_from_post(*, hook: str, body: str, cta: str, feature: str = "", benefit: str = "") -> list[dict[str, Any]]:
    """Deterministically derives carousel slides from an already-approved
    caption, rather than a second Gemini call — the carousel always matches
    what the caption says, never drifts from it. Splits body into short
    bullet points (one per non-empty line/sentence), capped at 4 content
    slides between a title slide and a closing CTA slide (<=6 total)."""
    points = [p.strip() for p in body.replace(". ", ".\n").splitlines() if p.strip()]
    points = points[:4] or [body.strip()[:140]]

    slides: list[dict[str, Any]] = [
        {"type": "title", "visual": {"title": hook, "subtitle": feature or ""}},
    ]
    if benefit:
        slides.append({"type": "bullets", "visual": {"heading": feature, "points": [benefit, *points[:3]]}})
    else:
        slides.append({"type": "bullets", "visual": {"heading": "", "points": points}})
    slides.append({"type": "cta", "visual": {"title": cta or "Try VyaparTrack free", "subtitle": "Free 6-month trial, no card required"}})
    return slides
