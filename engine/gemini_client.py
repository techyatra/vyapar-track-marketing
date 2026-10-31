"""Thin shared wrapper around the Gemini free tier, used by every content
and safety-check call.

Uses the current `google-genai` SDK, not the deprecated
`google-generativeai` package techyatra/youtube-automator was built against
— that package stopped receiving updates, and its pinned model
(gemini-2.0-flash) has since been retired by Google outright (confirmed by
a live 404 while building this), not just deprecated. A "set up once"
system can't be left depending on a dead package."""

from __future__ import annotations

import json
import os
import time

DEFAULT_MODEL = "gemini-3.8-flash"

# The SDK already retries transient errors internally before raising, so by
# the time one reaches here Google's free tier has genuinely been under
# sustained load for a while (confirmed live: a single call can take
# several minutes before failing). This is a second, longer-patience retry
# layer on top, because a 24-hours-later retry (next day's cron) is a bad
# fallback for something that often clears in under a minute.
MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = (10, 30, 60)


def generate(prompt: str, *, api_key: str | None = None, model: str = DEFAULT_MODEL) -> str:
    from google import genai
    from google.genai import errors as genai_errors

    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)

    last_exc: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text
        except genai_errors.ServerError as exc:
            last_exc = exc
            if attempt < MAX_ATTEMPTS - 1:
                wait = RETRY_BACKOFF_SECONDS[attempt]
                print(f"[gemini_client] {exc} — retrying in {wait}s (attempt {attempt + 1}/{MAX_ATTEMPTS})")
                time.sleep(wait)
    raise last_exc  # type: ignore[misc]


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
