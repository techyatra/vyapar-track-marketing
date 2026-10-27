"""Shared Supabase client. Jobs use the service_role key (bypasses RLS); the
browser approval dashboard uses the anon key + Supabase Auth instead — see
docs/approve/index.html, which never goes through this module.

SUPABASE_URL/SUPABASE_SERVICE_KEY point at the SAME Supabase project as
techyatra/Linkedin-Automator (by design — see README "Reusing Linkedin-
Automator's Supabase project"). Every table this engine touches is prefixed
vt_ (see supabase/schema.sql) so it can never collide with or accidentally
read Linkedin-Automator's own tables in that project."""

from __future__ import annotations

import os


def get_client():
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)
