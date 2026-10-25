"""X (Twitter) has no posting here by design — the free API tier is
read-mostly and posting access needs a paid tier (Basic, ~$100+/mo), which
was declined for this project. This module only validates and formats X
content so it lands in the approval queue as `manual_x_ready`: you open the
dashboard, copy the tweet/thread, and paste it into X yourself.

If X posting access is ever purchased later, swap this for a real client
(tweepy or raw API calls) — the content_queue schema and approval flow don't
change, only the final publish step in main_publish.py.
"""

from __future__ import annotations

MAX_TWEET_CHARS = 280


def validate_and_format(*, hook: str, body: str, cta: str) -> dict:
    """Builds either a single tweet or a numbered thread from hook/body/cta,
    splitting on existing line breaks in `body` (the model is instructed to
    produce thread-ready line breaks for X). Returns copy-paste-ready text."""
    lines = [hook.strip()] if hook.strip() and hook.strip() not in body else []
    lines += [line.strip() for line in body.splitlines() if line.strip()]
    if cta.strip() and cta.strip() not in body:
        lines.append(cta.strip())

    if len(lines) <= 1 and len(lines[0] if lines else "") <= MAX_TWEET_CHARS:
        text = lines[0] if lines else ""
        return {"mode": "single", "tweets": [text], "copy_paste_text": text}

    numbered = [f"{i+1}/{len(lines)} {line}" for i, line in enumerate(lines)]
    oversize = [t for t in numbered if len(t) > MAX_TWEET_CHARS]
    if oversize:
        raise ValueError(f"{len(oversize)} tweet(s) exceed {MAX_TWEET_CHARS} chars; shorten the source lines")

    return {"mode": "thread", "tweets": numbered, "copy_paste_text": "\n\n".join(numbered)}
