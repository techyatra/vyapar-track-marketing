"""Shared Supabase client. Jobs use the service_role key (bypasses RLS); the
browser approval dashboard uses the anon key + Supabase Auth instead — see
docs/approve/index.html, which never goes through this module."""

from __future__ import annotations

import os


def get_client():
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)
