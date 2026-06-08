"""Auth Phase 1 (Emergent Google OAuth) — backend test suite.

Covers:
  - /api/auth/me  (401 unauth, 200 visitor, 200 guardian, 401 expired)
  - /api/auth/logout  (deletes session)
  - /api/auth/session (400 with no header)
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://milton-propagate.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

GUARDIAN_TOK = "qa_david_tok"
VISITOR_TOK = "qa_visitor_tok"
EXPIRED_TOK = "qa_expired_tok"


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


# ── /auth/me ────────────────────────────────────────────────────────────────

def test_me_no_token_returns_401():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401, r.text


def test_me_guardian_returns_correct_fields():
    r = requests.get(f"{API}/auth/me", headers=_hdr(GUARDIAN_TOK))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_id"] == "qa-david"
    assert body["email"] == "davebouchez@gmail.com"
    assert body["name"] == "David"
    assert body["role"] == "guardian"
    # all 5 keys present
    for k in ("user_id", "email", "name", "picture", "role"):
        assert k in body


def test_me_visitor_role_for_non_guardian_email():
    r = requests.get(f"{API}/auth/me", headers=_hdr(VISITOR_TOK))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "visitor.qa@example.com"
    assert body["role"] == "visitor"


def test_me_expired_session_returns_401():
    r = requests.get(f"{API}/auth/me", headers=_hdr(EXPIRED_TOK))
    assert r.status_code == 401, r.text


def test_me_invalid_token_returns_401():
    r = requests.get(f"{API}/auth/me", headers=_hdr("totally_bogus_token_xyz"))
    assert r.status_code == 401


# ── /auth/session ───────────────────────────────────────────────────────────

def test_session_post_missing_header_returns_400():
    r = requests.post(f"{API}/auth/session")
    assert r.status_code == 400


# ── /auth/logout ────────────────────────────────────────────────────────────

def test_logout_deletes_session():
    """Seed a throwaway session, log out with it, then /me should return 401."""
    # Use a fresh visitor session created via mongosh-style seed (call backend? no — use a unique token)
    # We'll re-seed via the visitor token: logout that token, confirm /me=401, then re-seed for other tests.
    import pymongo, os as _os, urllib.parse
    mongo_url = "mongodb://localhost:27017"
    client = pymongo.MongoClient(mongo_url)
    db = client["test_database"]

    db.user_sessions.delete_one({"session_token": "qa_logout_tok"})
    db.users.update_one(
        {"user_id": "qa-visitor"},
        {"$set": {"user_id": "qa-visitor", "email": "visitor.qa@example.com",
                  "name": "QA Visitor", "role": "visitor"}},
        upsert=True,
    )
    from datetime import datetime, timezone, timedelta
    db.user_sessions.insert_one({
        "user_id": "qa-visitor",
        "session_token": "qa_logout_tok",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
        "created_at": datetime.now(timezone.utc),
    })

    # Confirm it works
    r = requests.get(f"{API}/auth/me", headers=_hdr("qa_logout_tok"))
    assert r.status_code == 200

    # Logout
    r = requests.post(f"{API}/auth/logout", headers=_hdr("qa_logout_tok"))
    assert r.status_code == 200

    # Subsequent /me must 401
    r = requests.get(f"{API}/auth/me", headers=_hdr("qa_logout_tok"))
    assert r.status_code == 401

    # Confirm db row gone
    assert db.user_sessions.find_one({"session_token": "qa_logout_tok"}) is None


# ── regression: chamber still loads (Paige session start) ──────────────────

def test_hospitality_start_regression():
    """AppShell + IdentityBridge wiring must not regress chamber endpoints."""
    payload = {"user_name": "QA Regression", "user_id": "qa-regression-anon"}
    r = requests.post(f"{API}/hospitality/start", json=payload, timeout=30)
    # Accept 200/201; some session_start endpoints return wrapper objects.
    assert r.status_code in (200, 201), f"{r.status_code} {r.text[:300]}"
    body = r.json()
    # Common keys we expect in a session-start response
    assert any(k in body for k in ("session_id", "id", "ok", "session")), body
