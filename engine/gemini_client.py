"""Thin shared wrapper around the Gemini free tier, used by every content
and safety-check call. Same model/approach as techyatra/youtube-automator."""

from __future__ import annotations

import json
import os


def generate(prompt: str, *, api_key: str | None = None, model: str = "gemini-2.0-flash") -> str:
    import google.generativeai as genai

    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(model)
    response = gen_model.generate_content(prompt)
    return response.text


def strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def generate_json(prompt: str, *, required_fields: tuple[str, ...], api_key: str | None = None) -> dict:
    raw = generate(prompt, api_key=api_key)
    data = json.loads(strip_json_fences(raw))
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Gemini response missing {missing}: {raw!r}")
    return data
