# VyaparTrack Marketing Automation

A "set up once" social media content engine for **VyaparTrack** (GST billing +
inventory ERP for Indian FMCG distributors). Generates on-brand posts for
LinkedIn, Instagram, Facebook, X, and YouTube Shorts on a schedule, runs an
automated compliance check, and queues everything for a single approver to
review before it goes live — then publishes automatically once approved.

Built on the same proven, free-tier pattern as `techyatra/Linkedin-Automator`
and `techyatra/youtube-automator`:

| Piece | Tool | Cost |
|---|---|---|
| Scheduling | GitHub Actions cron | Free |
| State (drafts, approvals, tokens, analytics) | Supabase (Postgres) | Free tier |
| Content writing + compliance check | Gemini API | Free tier |
| YouTube Short voice | `edge-tts` | Free, no API key |
| YouTube Short visuals | HTML/CSS/JS rendered via Playwright + ffmpeg | Free |
| IG/FB post graphic | Same HTML+Playwright technique | Free |
| Approval dashboard | Static page on GitHub Pages + Supabase Auth | Free |

## Why there's a human in the loop here (and not in youtube-automator)

`techyatra/youtube-automator` runs with **zero** human review — a dev-tips
mistake is cheap to live down. This project is B2B marketing copy for
paid software; a wrong claim is more reputationally costly, so **every
platform here queues for your approval** before publishing (the brief's
"zero review everywhere" option was declined for this reason). The
automated Gemini safety-check still runs on every draft first — it flags
fabricated numbers, overclaiming, and tax-advice-as-fact — so by the time
you see a draft, you're judging tone and accuracy, not catching the planted
compliance footguns yourself.

## How it works

```
scripts/run_scheduled_generation.py   (daily-generate.yml, picks platforms from config/posting_schedule.json)
  -> engine/topic_picker.py           (Gemini: weighted content pillar + topic, avoiding repeats)
  -> engine/content_writer.py         (Gemini: writes the post using prompts/system_prompt.md + platform_rules.md)
  -> engine/safety_check.py           (Gemini: compliance check — fabricated data, tax-advice-as-fact, overclaiming)
  -> Supabase content_queue, status='pending_approval'

docs/approve/index.html               (you review here — GitHub Pages + Supabase Auth, restricted to hello.vyapartrack@gmail.com)
  -> Approve / Reject updates content_queue.status

main_publish.py                       (publish-approved.yml, every 2 hours)
  -> linkedin, facebook: posted immediately via their APIs
  -> instagram: a branded graphic is rendered, committed to this repo, then posted
  -> youtube: voice (edge-tts) + render (Playwright/ffmpeg) + thumbnail + upload, THEN posted
  -> x: never auto-posted (see "X" below) — flipped to manual_x_ready with copy-paste text
```

## First-time setup

Do these in order. Everything below uses **hello.vyapartrack@gmail.com** —
use that account for every signup/consent screen.

### 0. Prerequisites

```bash
git clone https://github.com/techyatra/vyapar-track-marketing
cd vyapar-track-marketing
pip install -r requirements.txt
playwright install chromium   # only needed for local testing of the YouTube/graphic renderers
```

### 1. Gemini API key (free)

1. Go to https://aistudio.google.com, sign in as hello.vyapartrack@gmail.com
2. Get API Key → Create API Key. No credit card required.
3. Save it — you'll add it as a GitHub Secret in step 7.

### 2. Supabase project (free tier)

1. Go to https://supabase.com, sign up / sign in as hello.vyapartrack@gmail.com
2. New project → name it `vyapar-track-marketing`, pick a region close to India
   (ap-south-1 / Mumbai if offered), set a database password (save it — you
   won't need it day-to-day, but keep it somewhere safe).
3. Once provisioned: SQL Editor → paste the entire contents of
   `supabase/schema.sql` → Run.
4. Project Settings → API: copy the **Project URL**, the **anon public** key,
   and the **service_role** key (click to reveal). You'll need all three.
5. Authentication → Providers → make sure **Email** is enabled (it is by
   default). Authentication → URL Configuration → add your GitHub Pages URL
   (see step 6) to **Redirect URLs** once you know it, e.g.
   `https://techyatra.github.io/vyapar-track-marketing/approve/`.

### 3. LinkedIn (same pattern as techyatra/Linkedin-Automator)

1. Go to https://www.linkedin.com/developers/apps, sign in as
   hello.vyapartrack@gmail.com (or use a personal profile you control — the
   app posts as whichever profile authorizes it).
2. Create app → link it to a LinkedIn Company Page (required by LinkedIn
   even if you post to a personal profile) → request the **Share on
   LinkedIn** and **Sign In with LinkedIn using OpenID Connect** products
   (self-serve, approved instantly).
3. Auth tab → add redirect URL: `http://localhost:8765/callback`
4. Note the **Client ID** and **Client Secret** from the Auth tab.
5. Run locally:
   ```bash
   python scripts/linkedin_oauth_setup.py <client_id> <client_secret>
   ```
   This opens a browser, you approve as hello.vyapartrack@gmail.com, and it
   prints `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_REFRESH_TOKEN` (if your app has
   the refresh-token product — see the script's own note if not),
   `LINKEDIN_PERSON_URN`.
6. To post as a Company Page instead of a personal profile: find your
   organization's URN (`urn:li:organization:{id}`, visible in the Page
   admin URL) and set it as `LINKEDIN_ORG_URN`.
7. **Token lifetime:** access tokens last 60 days. `oauth-refresh.yml` runs
   monthly and rotates it automatically if your app has refresh-token
   access; otherwise it'll fail loudly and you re-run step 5.

### 4. Meta — Instagram + Facebook (the real steps, not instant)

This is the one platform that genuinely takes real setup time — budget
**1-2 weeks**, mostly waiting on Meta's review, not your own effort.

1. **Instagram account:** convert to a **Business** account (Instagram app →
   Settings → Account type → switch to Professional → Business) — must be
   done from the account itself, as hello.vyapartrack@gmail.com if that's
   the account email, or whichever Instagram account VyaparTrack will use.
2. **Facebook Page:** create one (facebook.com/pages/create) if you don't
   have one, logged in as hello.vyapartrack@gmail.com.
3. **Link them:** Instagram app → Settings → Account → Linked accounts →
   connect the Facebook Page you just made.
4. **Meta for Developers app:** go to https://developers.facebook.com/apps,
   create an app (type: **Business**), sign in as hello.vyapartrack@gmail.com.
5. Add the **Instagram Graph API** and **Facebook Login for Business**
   products to the app.
6. **Business verification:** Meta Business Suite → Business Settings →
   Business Info → Start Verification. Needs a real business document
   (GST certificate, incorporation certificate, or similar for VyaparTrack).
   This step is what takes the longest — Meta reviews can take several days.
7. **App Review:** request `instagram_content_publish`,
   `pages_manage_posts`, `pages_read_engagement`. You must submit a short
   screen-recording showing the use case (posting VyaparTrack marketing
   content) — Meta's reviewers watch it manually. Typically 3-7 days once
   business verification is done.
8. Once approved, Graph API Explorer (developers.facebook.com/tools/explorer)
   → select your app, your Page → generate a **Page Access Token** with
   `pages_manage_posts`, `pages_read_engagement`,
   `instagram_content_publish` scopes.
9. Exchange it for a long-lived token (60 days) — `scripts/oauth_refresh.py`
   does this monthly once you've set `META_APP_ID`/`META_APP_SECRET`, but do
   it once manually first via Graph API Explorer's token debugger
   ("Extend Access Token").
10. Find your `META_IG_USER_ID` (Instagram Business account's internal ID,
    not your @handle) via `GET /{page-id}?fields=instagram_business_account`
    in Graph API Explorer, and your `META_FB_PAGE_ID`.

**Until App Review is approved, `main_publish.py` will fail on Instagram/
Facebook rows — they'll just show as `failed` in the queue and retry on the
next run once your token works.** Everything else (LinkedIn, X copy, YouTube)
runs independently and isn't blocked by this.

### 5. X (Twitter) — scoped out of auto-posting

You chose **manual posting** for X: the free API tier can't post at all, and
the paid Basic tier (~$100+/month) wasn't worth it for this project. So:

- X drafts ARE generated and safety-checked on the same schedule as the
  other platforms.
- Once you approve a draft in the dashboard, `main_publish.py` flips it to
  `manual_x_ready` instead of calling any API.
- The "X — copy & paste" tab in the approval dashboard shows the exact
  tweet/thread text with a **Copy** button — paste it into X yourself.

If you later decide to pay for API access, `engine/x_formatter.py` is where
real posting would go — the queue/approval flow doesn't change.

### 6. YouTube (same pattern as techyatra/youtube-automator)

1. https://console.cloud.google.com → new project (or reuse one), signed in
   as hello.vyapartrack@gmail.com.
2. APIs & Services → Library → **YouTube Data API v3** → Enable.
3. APIs & Services → OAuth consent screen: User type **External**, add scope
   `.../auth/youtube.upload`, add hello.vyapartrack@gmail.com as a **Test
   user**. (Submit for verification → Production later to avoid the 7-day
   idle-refresh-token expiry; not required to start, since this runs daily.)
4. APIs & Services → Credentials → Create Credentials → OAuth client ID →
   **Desktop app** → download `client_secret.json`.
5. Run locally:
   ```bash
   python scripts/youtube_oauth_setup.py path/to/client_secret.json
   ```
   Prints `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.
6. Make sure the YouTube channel posting (the one tied to
   hello.vyapartrack@gmail.com, or whichever Google account owns the
   VyaparTrack channel) is the account you authorize in the browser step.

### 7. Add GitHub Secrets

Repo → Settings → Secrets and variables → Actions → New repository secret.
Add:

```
GEMINI_API_KEY
SUPABASE_URL
SUPABASE_SERVICE_KEY
LINKEDIN_CLIENT_ID
LINKEDIN_CLIENT_SECRET
LINKEDIN_ACCESS_TOKEN
LINKEDIN_REFRESH_TOKEN        (if your app has the refresh-token product)
LINKEDIN_PERSON_URN
LINKEDIN_ORG_URN              (optional, only if posting as a Company Page)
META_APP_ID
META_APP_SECRET
META_PAGE_ACCESS_TOKEN
META_IG_USER_ID
META_FB_PAGE_ID
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN
```

(LinkedIn/Meta secrets can be added later — generation and the approval
dashboard work without them; only `main_publish.py` needs them, and only for
the platforms it's actually posting to.)

### 8. Turn on the approval dashboard (GitHub Pages)

1. Repo → Settings → Pages → Source: **Deploy from a branch** → Branch:
   `main`, folder `/docs` → Save.
2. It'll be live at `https://techyatra.github.io/vyapar-track-marketing/approve/`
   within a minute or two.
3. Open it, expand "Configure Supabase connection", paste your Supabase
   **Project URL** and **anon public** key (from step 2.4) — these aren't
   secret (RLS in `supabase/schema.sql` restricts all access to
   `hello.vyapartrack@gmail.com`), stored only in your browser's
   localStorage.
4. Enter hello.vyapartrack@gmail.com → Send magic link → check that inbox →
   click the link → you're in.
5. Bookmark it. This is the only manual step in the whole system going
   forward: open the bookmark, Approve/Reject what's pending.

### 9. Test it before trusting it

```bash
cp config/settings.example.json config/settings.json   # edit if you want different cadence/voice
export GEMINI_API_KEY=... SUPABASE_URL=... SUPABASE_SERVICE_KEY=...
python main_generate.py --platform linkedin --count 1
python main_youtube_short.py
```
Check the Supabase `content_queue` table (or the dashboard) for the new
rows. Render pipeline only (no network calls, verifies Playwright+ffmpeg):
```bash
python scripts/smoke_test_render.py
```
Or trigger `daily-generate.yml` manually once (Actions tab → "Generate daily
content drafts" → Run workflow) before trusting the cron schedule.

### 10. Turn it on

Once you're happy with a few manually-triggered runs, the cron schedules in
`.github/workflows/` take over:

- **daily-generate.yml** — 6:00 AM IST daily, generates that day's drafts
  per `config/posting_schedule.json`
- **publish-approved.yml** — every 2 hours, publishes anything you approved
- **fetch-analytics.yml** — 11:00 PM IST daily
- **oauth-refresh.yml** — 1st of every month

Nothing else to run manually except opening the approval dashboard.

## Posting cadence

As specified in the original brief (`config/content_pillars.json
cadence_per_week`): LinkedIn 3/wk, X 6/wk, Instagram ~5/wk, Facebook ~4/wk,
YouTube Shorts 2/wk — spread across the week by
`config/posting_schedule.json`. Edit that file to change which days get
which platforms.

## Known limitations (so nothing here is oversold)

- **Instagram/Facebook visuals are a single branded graphic**, not a real
  4-6 slide carousel or a reel. `engine/graphic_generator.py` renders one
  on-brand hook/stat image per post — enough to satisfy Instagram's "every
  post needs media" requirement, not the richer carousel/reel formats the
  original brief describes. Building real carousels or short-form video for
  IG is a natural next step, not yet built.
- **X has no posting API integration** — by your choice, to avoid the paid
  tier. Content is generated and queued; you paste it in manually.
- **Meta posting is blocked until App Review completes** (step 4) — budget
  1-2 weeks before Instagram/Facebook can actually go live, even though
  everything else works immediately.
- **LinkedIn refresh tokens** require your app to be approved for LinkedIn's
  refresh-token product; without it you re-run
  `scripts/linkedin_oauth_setup.py` every ~55 days (a 60-day access token).
- **The Gemini safety check is a net, not a guarantee** — same caveat as
  youtube-automator: it catches fabricated numbers and obvious compliance
  issues, but you are the actual reviewer for every post before it's live.

## Project layout

```
prompts/
  system_prompt.md          The VyaparTrack brand voice + hard rules (edit this to change tone)
  platform_rules.md         Per-platform format rules
config/
  settings.example.json     Copy to settings.json — brand colors, YouTube render settings
  content_pillars.json      The 6 pillars, weights, feature pool, cadence
  posting_schedule.json     Weekday -> platforms (implements the cadence)
  hashtag_bank.json
engine/
  gemini_client.py          Shared Gemini wrapper
  supabase_client.py        Shared Supabase (service_role) client
  topic_picker.py           Weighted pillar + topic selection, avoiding repeats
  content_writer.py         The actual post generator (LinkedIn/IG/FB/X/YouTube script)
  safety_check.py           Automated compliance check
  linkedin_poster.py        LinkedIn REST API posting + token refresh
  meta_poster.py            Instagram/Facebook Graph API posting + token exchange
  x_formatter.py            Formats X content for manual copy-paste (no posting API)
  graphic_generator.py      Branded IG/FB graphic (HTML + Playwright)
  youtube/
    scene_renderer.py       HTML/CSS/JS scenes -> Playwright frames -> ffmpeg -> MP4 (from youtube-automator)
    voice_generator.py      edge-tts + word timing (from youtube-automator)
    thumbnail_generator.py  Thumbnail PNG via Playwright (from youtube-automator)
    youtube_uploader.py     Unattended upload via refresh token (from youtube-automator)
templates/
  scene.html                 Video scene template, rebranded (title/text/stat/feature/comparison/outro)
  thumbnail.html             YouTube thumbnail template, rebranded
  graphic.html                IG/FB post graphic template
docs/
  approve/index.html          The approval dashboard (GitHub Pages + Supabase Auth)
  generated/                   Committed IG graphics land here (so they have a public raw URL)
supabase/
  schema.sql                   Full schema: topics, content_queue, oauth_tokens, post_analytics, automation_runs
scripts/
  youtube_oauth_setup.py        Run once locally to mint the YouTube refresh token
  linkedin_oauth_setup.py       Run once locally to mint the LinkedIn access/refresh token
  oauth_refresh.py              Rotates LinkedIn/Meta tokens (run by oauth-refresh.yml)
  fetch_analytics.py            Pulls engagement metrics (run by fetch-analytics.yml)
  run_scheduled_generation.py   Reads posting_schedule.json, generates today's drafts
  smoke_test_render.py          Local render pipeline test, no network calls
main_generate.py                 One draft for a given text platform
main_youtube_short.py            One YouTube Short SCRIPT (rendering deferred to publish time)
main_publish.py                  Publishes every approved row
.github/workflows/
  daily-generate.yml             6 AM IST daily
  publish-approved.yml           Every 2 hours
  fetch-analytics.yml            11 PM IST daily
  oauth-refresh.yml              Monthly
```
