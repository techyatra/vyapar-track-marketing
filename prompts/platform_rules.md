# Per-platform rules

Appended to the system prompt for every generation call, along with the
specific `{platform}` / `{content_pillar}` / `{topic}` / optional inputs for
that call. See `engine/content_writer.py`.

### PLATFORM RULES

**Instagram**
- Caption 125–220 words, punchy first line (shows before "more").
- Emoji-light but present. Line breaks for readability.
- 8–15 hashtags, mix broad + niche (see hashtag bank).
- Visual: carousel (educational, 4–6 slides) OR reel (15–30s problem→solution)
  OR single bold stat/quote graphic. Specify which.
- Reels get a spoken/overlay hook in the first 2 seconds.
- CTA: "DM 'DEMO'", "Link in bio", "Save this for GST filing".

**Facebook**
- Slightly longer, more explanatory than IG (150–250 words). Community tone.
- Good for local-distributor groups, how-to posts, feature explainers.
- 3–5 hashtags max. CTA to website/WhatsApp/demo booking.

**X (Twitter)**
- Single tweet ≤ 280 chars OR a 3–5 tweet thread for tips/breakdowns.
- Sharp, opinionated, one idea per tweet. Thread = numbered, strong hook tweet.
- 1–3 hashtags only. CTA in last tweet.

**LinkedIn**
- 150–300 words, professional but human. First 2 lines are the hook (pre-"see more").
- B2B angle: efficiency, compliance, scaling, owner/CA audience.
- Short paragraphs, occasional bullet list. 3–5 hashtags.
- No slang; minimal emoji. CTA: book a demo / comment / DM.

**YouTube**
- Produce: (a) Video title (≤60 chars, keyword-rich), (b) 150–250 word
  description with timestamps placeholder + CTA + links, (c) 10–15 tags,
  (d) a 45–90s short script OR a long-form video outline (hook, 3–5 sections,
  CTA) depending on topic, (e) thumbnail text (≤5 words, bold).

### HASHTAG BANK

See `config/hashtag_bank.json` — pick per platform.

### CONTENT PILLARS & CADENCE

See `config/content_pillars.json` for the 6 pillars, their weights, and the
per-platform weekly cadence.
