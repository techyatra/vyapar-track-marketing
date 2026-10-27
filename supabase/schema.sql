-- VyaparTrack Marketing Automation — Supabase schema
-- Run once in the Supabase SQL Editor, then reload the PostgREST schema
-- cache (Database -> API -> "Reload schema").
--
-- This project SHARES a Supabase project with techyatra/Linkedin-Automator
-- (its multi-tenant tables include topics_li, user_automation_settings,
-- tokens_li, etc. — see that repo's scripts/*.sql). Every table here is
-- prefixed vt_ (VyaparTrack) so nothing collides with that product's own
-- tables in the same database, and it's always obvious which rows belong to
-- which automation when browsing the Table Editor.
--
-- GitHub Actions jobs are stateless and read/write through here.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- 1. vt_topics: candidate topics discovered or hand-entered, queued for writing
-- ---------------------------------------------------------------------------
create table if not exists public.vt_topics (
  id uuid primary key default gen_random_uuid(),
  platform text not null check (platform in ('linkedin', 'instagram', 'facebook', 'x', 'youtube')),
  pillar_id text not null,
  topic text not null,
  angle text,
  status text not null default 'pending' check (status in ('pending', 'used', 'skipped')),
  created_at timestamptz not null default now(),
  used_at timestamptz
);

create index if not exists vt_topics_platform_status_idx on public.vt_topics (platform, status);

-- ---------------------------------------------------------------------------
-- 2. vt_content_queue: every generated post, from draft through published.
--    This is the single table the approval dashboard reads/writes.
-- ---------------------------------------------------------------------------
create table if not exists public.vt_content_queue (
  id uuid primary key default gen_random_uuid(),
  platform text not null check (platform in ('linkedin', 'instagram', 'facebook', 'x', 'youtube')),
  pillar_id text not null,
  topic text not null,

  -- Generated content (see engine/content_writer.py output schema)
  hook text,
  body text,
  cta text,
  hashtags text[],
  visual_direction text,
  alt_text text,
  best_time_ist text,

  -- YouTube-only extra fields
  yt_title text,
  yt_description text,
  yt_tags text[],
  yt_thumbnail_text text,
  yt_video_path text,
  yt_thumbnail_path text,

  -- Instagram/Facebook visual asset type (engine/content_writer.classify_visual_type,
  -- from the model's own visual_direction text). 'reel_script' is populated only
  -- when visual_type = 'reel' (see engine/content_writer.write_reel_script).
  visual_type text not null default 'single_graphic'
    check (visual_type in ('single_graphic', 'carousel', 'reel')),
  reel_script jsonb,

  -- Safety check (engine/safety_check.py) — the automated net before human review
  safety_safe boolean,
  safety_concerns text[],
  safety_reasoning text,

  -- Approval queue workflow. X always stops at 'approved' (no posting API);
  -- everything else proceeds to 'published' once main_publish.py posts it.
  status text not null default 'pending_approval'
    check (status in ('pending_approval', 'approved', 'rejected', 'published', 'manual_x_ready', 'failed')),
  reviewer_note text,
  reviewed_at timestamptz,
  reviewed_by text,

  scheduled_for timestamptz,
  published_at timestamptz,
  platform_post_id text,
  platform_post_url text,

  created_at timestamptz not null default now()
);

create index if not exists vt_content_queue_status_idx on public.vt_content_queue (status);
create index if not exists vt_content_queue_platform_idx on public.vt_content_queue (platform, created_at desc);

-- ---------------------------------------------------------------------------
-- 3. vt_oauth_tokens: per-platform refresh tokens, refreshed by oauth-refresh.yml
--    (This project's own tokens — distinct from Linkedin-Automator's
--    per-user tokens_li / user_automation_settings tables.)
-- ---------------------------------------------------------------------------
create table if not exists public.vt_oauth_tokens (
  platform text primary key check (platform in ('linkedin', 'youtube', 'meta')),
  access_token text,
  refresh_token text,
  expires_at timestamptz,
  extra jsonb default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 4. vt_post_analytics: engagement snapshots pulled by fetch-analytics.yml
-- ---------------------------------------------------------------------------
create table if not exists public.vt_post_analytics (
  id uuid primary key default gen_random_uuid(),
  vt_content_queue_id uuid references public.vt_content_queue(id) on delete cascade,
  platform text not null,
  impressions integer,
  likes integer,
  comments integer,
  shares integer,
  clicks integer,
  fetched_at timestamptz not null default now()
);

create index if not exists vt_post_analytics_content_idx on public.vt_post_analytics (vt_content_queue_id);

-- ---------------------------------------------------------------------------
-- 5. vt_automation_runs: one row per GitHub Actions job run, for debugging
-- ---------------------------------------------------------------------------
create table if not exists public.vt_automation_runs (
  id uuid primary key default gen_random_uuid(),
  job_name text not null,
  status text not null check (status in ('success', 'failure')),
  summary text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
-- GitHub Actions jobs authenticate with the service_role key, which bypasses
-- RLS entirely — so these policies only matter for the browser-based approval
-- dashboard, which uses the anon key. Lock it down to the single approver
-- email, authenticated via Supabase email OTP/magic link. This also keeps
-- the dashboard from ever being able to read/write Linkedin-Automator's own
-- tables in this shared project — it only ever queries vt_* tables.

alter table public.vt_content_queue enable row level security;
alter table public.vt_topics enable row level security;
alter table public.vt_post_analytics enable row level security;

drop policy if exists "approver_full_access" on public.vt_content_queue;
create policy "approver_full_access" on public.vt_content_queue
  for all
  using (auth.jwt() ->> 'email' = 'hello.vyapartrack@gmail.com')
  with check (auth.jwt() ->> 'email' = 'hello.vyapartrack@gmail.com');

drop policy if exists "approver_read_topics" on public.vt_topics;
create policy "approver_read_topics" on public.vt_topics
  for select
  using (auth.jwt() ->> 'email' = 'hello.vyapartrack@gmail.com');

drop policy if exists "approver_read_analytics" on public.vt_post_analytics;
create policy "approver_read_analytics" on public.vt_post_analytics
  for select
  using (auth.jwt() ->> 'email' = 'hello.vyapartrack@gmail.com');

-- vt_oauth_tokens and vt_automation_runs are never touched by the browser —
-- no policies needed; only the service_role key (used by GitHub Actions) can
-- read/write them once RLS is enabled with zero policies for anon/authenticated.
alter table public.vt_oauth_tokens enable row level security;
alter table public.vt_automation_runs enable row level security;
