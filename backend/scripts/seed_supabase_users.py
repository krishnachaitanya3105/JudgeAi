"""
Seed Supabase Auth users + public.users role profiles for JudgeAI.

Usage:
  python backend/scripts/seed_supabase_users.py

Required env:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY as fallback)
"""

import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SERVICE_KEY:
    raise SystemExit(
        "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY in .env"
    )


SEED_USERS = [
    {
        "email": "admin@judgeai.local",
        "password": "admin123",
        "full_name": "Admin",
        "role": "admin",
        "department": "Central Administration",
    },
    {
        "email": "officer@judgeai.local",
        "password": "officer123",
        "full_name": "Officer",
        "role": "officer",
        "department": "Ministry of Environment",
    },
]


def auth_headers():
    return {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def create_auth_user(user):
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    payload = {
        "email": user["email"],
        "password": user["password"],
        "email_confirm": True,
        "user_metadata": {"role": user["role"], "full_name": user["full_name"]},
    }
    response = requests.post(url, headers=auth_headers(), json=payload, timeout=30)
    if response.status_code in (200, 201):
        print(f"[auth] created {user['email']}")
        return
    if response.status_code in (400, 422) and "already" in response.text.lower():
        print(f"[auth] exists   {user['email']}")
        return
    raise RuntimeError(f"[auth] failed {user['email']}: {response.status_code} {response.text}")


def upsert_profile(user):
    url = f"{SUPABASE_URL}/rest/v1/users"
    payload = {
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "department": user["department"],
        "is_active": True,
    }
    headers = auth_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code in (200, 201):
        print(f"[db]   upserted {user['email']}")
        return
    raise RuntimeError(f"[db] failed {user['email']}: {response.status_code} {response.text}")


def main():
    print("Seeding Supabase users for JudgeAI...")
    for user in SEED_USERS:
        create_auth_user(user)
        upsert_profile(user)
    print("Done.")


if __name__ == "__main__":
    main()
