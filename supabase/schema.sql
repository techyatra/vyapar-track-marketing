-- VyaparTrack Marketing Automation — Supabase schema
-- Run once in the Supabase SQL Editor for a new project, then reload the
-- PostgREST schema cache (Database -> API -> "Reload schema").
--
-- Mirrors the proven techyatra/Linkedin-Automator pattern: Supabase holds all
-- durable state (topics, drafts, approval queue, schedules, analytics, OAuth
-- tokens); GitHub Actions jobs are stateless and read/write through here.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- 1. topics: candidate topics discovered or hand-entered, queued for writing
-- ---------------------------------------------------------------------------
create table if not exists public.topics (
  id uuid primary key default gen_random_uuid(),
  platform text not null check (platform in ('linkedin', 'instagram', 'facebook', 'x', 'youtube')),
  pillar_id text not null,
  topic text not null,
  angle text,
  status text not null default 'pending' check (status in ('pending', 'used', 'skipped')),
  created_at timestamptz not null default now(),
  used_at timestamptz
);

create index if not exists topics_platform_status_idx on public.topics (platform, status);

-- ---------------------------------------------------------------------------
-- 2. content_queue: every generated post, from draft through published.
--    This is the single table the approval dashboard reads/writes.
-- ---------------------------------------------------------------------------
create table if not exists public.content_queue (
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

create index if not exists content_queue_status_idx on public.content_queue (status);
create index if not exists content_queue_platform_idx on public.content_queue (platform, created_at desc);

-- ---------------------------------------------------------------------------
-- 3. oauth_tokens: per-platform refresh tokens, refreshed by oauth-refresh.yml
-- ---------------------------------------------------------------------------
create table if not exists public.oauth_tokens (
  platform text primary key check (platform in ('linkedin', 'youtube', 'meta')),
  access_token text,
  refresh_token text,
  expires_at timestamptz,
  extra jsonb default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 4. post_analytics: engagement snapshots pulled by fetch-analytics.yml
-- ---------------------------------------------------------------------------
create table if not exists public.post_analytics (
  id uuid primary key default gen_random_uuid(),
  content_queue_id uuid references public.content_queue(id) on delete cascade,
  platform text not null,
  impressions integer,
  likes integer,
  comments integer,
  shares integer,
  clicks integer,
  fetched_at timestamptz not null default now()
);

create index if not exists post_analytics_content_idx on public.post_analytics (content_queue_id);

-- ---------------------------------------------------------------------------
-- 5. automation_runs: one row per GitHub Actions job run, for debugging
-- ---------------------------------------------------------------------------
create table if not exists public.automation_runs (
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
-- email set as APPROVER_EMAIL, authenticated via Supabase email OTP/magic link.

alter table public.content_queue enable row level security;
alter table public.topics enable row level security;
alter table public.post_analytics enable row level security;

drop policy if exists "approver_full_access" on public.content_queue;
create policy "approver_full_access" on public.content_queue
  for all
  using (auth.jwt() ->> 'email' = 'hello.vyapartrack@gmail.com')
  with check (auth.jwt() ->> 'email' = 'hello.vyapartrack@gmail.com');

drop policy if exists "approver_read_topics" on public.topics;
create policy "approver_read_topics" on public.topics
  for select
  using (auth.jwt() ->> 'email' = 'hello.vyapartrack@gmail.com');

drop policy if exists "approver_read_analytics" on public.post_analytics;
create policy "approver_read_analytics" on public.post_analytics
  for select
  using (auth.jwt() ->> 'email' = 'hello.vyapartrack@gmail.com');

-- oauth_tokens and automation_runs are never touched by the browser — no
-- policies needed; only the service_role key (used by GitHub Actions) can
-- read/write them once RLS is enabled with zero policies for anon/authenticated.
alter table public.oauth_tokens enable row level security;
alter table public.automation_runs enable row level security;
