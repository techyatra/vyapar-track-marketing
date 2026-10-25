"""Automated pre-publish compliance check — the one safety net standing
between a generated post and the approval queue, same role as
techyatra/youtube-automator's content_safety_check.py.

Even with human approval in the loop (review_policy = queue_for_approval),
this runs BEFORE the post reaches the queue, so the reviewer never has to
spot fabricated numbers or compliance violations themselves — they only
judge tone/quality. Any flagged post is still queued, just with
safety_safe=false and the concerns visible, so the approver can reject it
outright rather than relying on the pipeline to have caught everything.
"""

from __future__ import annotations

from .gemini_client import generate_json

PROMPT_TEMPLATE = """You are a conservative pre-publish compliance reviewer for a \
VyaparTrack (B2B GST/ERP software) social media post. VyaparTrack sells to \
Indian FMCG distributors; copy mistakes here are reputationally costly \
because this is regulated-adjacent (GST) B2B software, not consumer content.

Post content:
Hook: {hook}
Body: {body}
CTA: {cta}

Check specifically for:
1. Fabricated data: invented GST numbers, phone numbers, prices, discount
   percentages, customer names, testimonials, or statistics not provided as
   input.
2. Tax/legal claims stated as settled fact rather than "how VyaparTrack helps
   you handle X" framing.
3. Misleading or unprovable superlatives ("best", "#1", "fastest", "guaranteed").
4. Fear-mongering about GST penalties or compliance consequences.
5. Any claim inconsistent with VyaparTrack's actual feature set (multi-firm
   billing, GST automation, inventory/FIFO costing, ITC tracking — not
   payroll, not POS hardware, not anything outside FMCG distribution ERP).

Respond with ONLY a JSON object, no markdown fences, no commentary:
{{
  "safe": true or false,
  "concerns": ["short description of each concern found, empty list if none"],
  "reasoning": "one sentence explaining the verdict"
}}
"""


def check_post_safety(*, hook: str, body: str, cta: str, api_key: str | None = None) -> dict:
    data = generate_json(
        PROMPT_TEMPLATE.format(hook=hook, body=body, cta=cta),
        required_fields=("safe", "concerns", "reasoning"),
        api_key=api_key,
    )
    return data


def check_youtube_script_safety(*, title: str, description: str, scenes: list[dict], api_key: str | None = None) -> dict:
    narration = "\n".join(f"- {s['narration']}" for s in scenes)
    return check_post_safety(hook=title, body=f"{description}\n\nNarration:\n{narration}", cta="", api_key=api_key)
