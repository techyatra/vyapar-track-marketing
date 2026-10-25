"""Generates one ready-to-publish post, using the exact system prompt +
platform rules in prompts/system_prompt.md and prompts/platform_rules.md.

Output schema (see prompts/system_prompt.md "OUTPUT FORMAT"):
    platform, hook, body, cta, hashtags, visual_direction, alt_text, best_time_ist
YouTube additionally returns: yt_title, yt_description, yt_tags,
yt_thumbnail_text, yt_script (list of scenes) or yt_outline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .gemini_client import generate_json

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

TRIGGER_TEMPLATE = """{system_prompt}

{platform_rules}

---

Generate ONE post for **{platform}**.
Content pillar: **{pillar_name}**
Topic / angle: **{topic}** — {angle}
Optional inputs (use only if provided, else ignore): offer={offer}, feature={feature}, stat={stat}, event={event}.

Follow all rules and the output format from the system block. Match the
platform conventions exactly. Respond with ONLY the JSON object described in
OUTPUT FORMAT — no markdown fences, no commentary.
"""

YOUTUBE_SCENE_TYPES = """
- "title_card": big title text. visual: {"title": str, "subtitle": str}
- "text_point": one short statement/kinetic text on screen. visual: {"text": str}
- "stat_card": one big number/fact (only if given as input, never fabricated). visual: {"stat": str, "label": str}
- "comparison": two-column before/after (e.g. Tally+Excel vs VyaparTrack). visual: {"left_label": str, "left_text": str, "right_label": str, "right_text": str}
- "feature_card": one feature, named + one-line benefit. visual: {"feature": str, "benefit": str}
- "outro_card": closing CTA. visual: {"title": str, "subtitle": str}
"""

YOUTUBE_TRIGGER_TEMPLATE = """{system_prompt}

Generate a YouTube Short for VyaparTrack.
Content pillar: **{pillar_name}**
Topic / angle: **{topic}** — {angle}
Optional inputs (use only if provided, else ignore): offer={offer}, feature={feature}, stat={stat}, event={event}.

Rules:
- The hook (first scene) must grab attention in under 3 seconds.
- Write narration as natural spoken sentences, not bullet fragments.
- Never invent numbers, pricing, or customer counts not given as input.
- End with a concrete CTA (free 6-month trial, no card needed, worked into the
  outro_card naturally).
- 4 to 7 scenes total. Each scene's narration should take roughly 4-9 seconds
  to speak aloud (~2.5 words/second), 45-70 seconds total.
- Use these scene types only:
{scene_types}

Respond with ONLY a JSON object, no markdown fences, no commentary:
{{
  "yt_title": "<=60 chars, keyword-rich, no clickbait lies",
  "yt_description": "150-250 word YouTube description with a CTA and a [TIMESTAMPS] placeholder line",
  "yt_tags": ["10 to 15 relevant tags"],
  "yt_thumbnail_text": "<=5 words, bold",
  "best_time_ist": "suggested publish day/time",
  "yt_script": [
    {{"type": "title_card", "narration": "...", "visual": {{...fields for this type...}}}},
    ...
  ]
}}
"""


def _load_prompt_blocks() -> tuple[str, str]:
    system_prompt = (PROMPTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    platform_rules = (PROMPTS_DIR / "platform_rules.md").read_text(encoding="utf-8")
    return system_prompt, platform_rules


def write_post(
    *,
    platform: str,
    pillar_name: str,
    topic: str,
    angle: str,
    offer: str = "",
    feature: str = "",
    stat: str = "",
    event: str = "",
    api_key: str | None = None,
) -> dict[str, Any]:
    system_prompt, platform_rules = _load_prompt_blocks()

    if platform == "youtube":
        prompt = YOUTUBE_TRIGGER_TEMPLATE.format(
            system_prompt=system_prompt,
            pillar_name=pillar_name,
            topic=topic,
            angle=angle,
            offer=offer,
            feature=feature,
            stat=stat,
            event=event,
            scene_types=YOUTUBE_SCENE_TYPES,
        )
        required = ("yt_title", "yt_description", "yt_tags", "yt_thumbnail_text", "yt_script")
    else:
        prompt = TRIGGER_TEMPLATE.format(
            system_prompt=system_prompt,
            platform_rules=platform_rules,
            platform=platform,
            pillar_name=pillar_name,
            topic=topic,
            angle=angle,
            offer=offer,
            feature=feature,
            stat=stat,
            event=event,
        )
        required = ("platform", "hook", "body", "cta", "hashtags", "visual_direction", "alt_text", "best_time_ist")

    data = generate_json(prompt, required_fields=required, api_key=api_key)
    if platform != "youtube" and not data["hashtags"]:
        raise ValueError("Gemini returned no hashtags")
    if platform == "youtube" and not data["yt_script"]:
        raise ValueError("Gemini returned a YouTube script with zero scenes")
    return data


def classify_visual_type(visual_direction: str) -> str:
    """The IG/FB platform rules ask the model to specify carousel/reel/graphic
    in its own visual_direction text — this just reads that back out, so the
    asset generator and the caption never disagree about what's being made."""
    text = (visual_direction or "").lower()
    if "carousel" in text:
        return "carousel"
    if "reel" in text:
        return "reel"
    return "single_graphic"


REEL_SCENE_TYPES = """
- "title_card": the hook, on screen for the first ~3 seconds. visual: {"title": str, "subtitle": str}
- "feature_card": one feature, named + one-line benefit. visual: {"feature": str, "benefit": str}
- "comparison": before/after (e.g. Tally+Excel vs VyaparTrack). visual: {"left_label": str, "left_text": str, "right_label": str, "right_text": str}
- "text_point": one short statement. visual: {"text": str}
- "outro_card": closing CTA. visual: {"title": str, "subtitle": str}
"""

REEL_TRIGGER_TEMPLATE = """{system_prompt}

Generate a 15-25 second Instagram/Facebook Reel script for VyaparTrack —
the same topic and angle as the caption already written for this post, so
they tell the same story; the narration does NOT need to match the caption
word-for-word, just the same idea.

Content pillar: **{pillar_name}**
Topic / angle: **{topic}** — {angle}
The caption already written for this post (for context — don't repeat it
verbatim as narration): {caption_hook} {caption_body}

Rules:
- The hook (first scene) must grab attention in under 2 seconds.
- Write narration as natural spoken sentences, not bullet fragments.
- Never invent numbers, pricing, or customer counts not given as input.
- 3 to 4 scenes total, 15-25 seconds total (~2.5 words/second).
- Use these scene types only:
{scene_types}

Respond with ONLY a JSON object, no markdown fences, no commentary:
{{
  "reel_script": [
    {{"type": "title_card", "narration": "...", "visual": {{...fields for this type...}}}},
    ...
  ]
}}
"""


def write_reel_script(
    *, pillar_name: str, topic: str, angle: str, caption_hook: str, caption_body: str, api_key: str | None = None
) -> dict[str, Any]:
    system_prompt, _ = _load_prompt_blocks()
    prompt = REEL_TRIGGER_TEMPLATE.format(
        system_prompt=system_prompt,
        pillar_name=pillar_name,
        topic=topic,
        angle=angle,
        caption_hook=caption_hook,
        caption_body=caption_body,
        scene_types=REEL_SCENE_TYPES,
    )
    data = generate_json(prompt, required_fields=("reel_script",), api_key=api_key)
    if not data["reel_script"]:
        raise ValueError("Gemini returned a reel script with zero scenes")
    return data


if __name__ == "__main__":
    import sys

    result = write_post(
        platform=sys.argv[1] if len(sys.argv) > 1 else "linkedin",
        pillar_name="Pain -> Solution",
        topic="Month-end GST filing panic across 3 firms",
        angle="Distributors running multiple GSTINs lose a whole night to reconciling books before every return.",
    )
    print(json.dumps(result, indent=2))
