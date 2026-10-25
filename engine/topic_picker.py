"""Picks the next (platform, pillar, topic) to write, avoiding recent repeats.

Mirrors techyatra/youtube-automator's topic_generator.py pattern, but pillar
selection is weighted from config/content_pillars.json rather than Gemini
free-forming it, so the 30/20/20/10/10/10 mix in the brief is enforced
deterministically rather than hoped for.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .gemini_client import generate_json

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

PROMPT_TEMPLATE = """You are a content strategist for VyaparTrack, a GST billing \
and inventory ERP for Indian FMCG distributors.

Platform: {platform}
Content pillar: {pillar_name} — {pillar_brief}
Feature pool (only used if the pillar is feature_spotlight; otherwise ignore): {feature_pool}

Avoid repeating any of these recently-covered topics:
{recent_topics}

Pick ONE specific, narrow topic + angle for a single post on this platform and
pillar. Be concrete (a specific pain, a specific feature, a specific GST
date/scenario) — never vague ("GST tips in general").

Respond with ONLY a JSON object, no markdown fences, no commentary:
{{
  "topic": "a specific, narrow topic in <= 15 words",
  "angle": "the specific hook/angle for this post in one sentence"
}}
"""


def _load_pillars() -> dict[str, Any]:
    return json.loads((CONFIG_DIR / "content_pillars.json").read_text(encoding="utf-8"))


def pick_pillar(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or _load_pillars()
    pillars = config["pillars"]
    weights = [p["weight"] for p in pillars]
    return random.choices(pillars, weights=weights, k=1)[0]


def pick_topic(
    *, platform: str, recent_topics: list[str], pillar: dict[str, Any] | None = None, api_key: str | None = None
) -> dict[str, Any]:
    config = _load_pillars()
    pillar = pillar or pick_pillar(config)

    data = generate_json(
        PROMPT_TEMPLATE.format(
            platform=platform,
            pillar_name=pillar["name"],
            pillar_brief=pillar["brief"],
            feature_pool=", ".join(config["feature_pool"]),
            recent_topics="\n".join(f"- {t}" for t in recent_topics) or "(none yet)",
        ),
        required_fields=("topic", "angle"),
        api_key=api_key,
    )
    data["pillar_id"] = pillar["id"]
    data["pillar_name"] = pillar["name"]
    return data
