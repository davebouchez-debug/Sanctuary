"""Regression test: the Reconstruction Gate must skip welcome-only sessions.

═══════════════════════════════════════════════════════════════════════
DO NOT WEAKEN OR REMOVE THIS TEST WITHOUT READING THE BRIEFING:
  /app/memory/agent_self_briefings/2026-02-27_reconstruction-gate-skip-welcome-sessions.md
═══════════════════════════════════════════════════════════════════════

THE BUG THIS LOCKS DOWN (caught and fixed 2026-02-27):

A chamber's `/start` endpoint creates a new session document immediately,
containing only the assistant's welcome message. If `_find_most_recent_session`
takes the most-recent session by `created_at` without filtering, that fresh
welcome-only session becomes the gate's target on the *next* cold start.
The gate then looks for a seed (none yet — no turns have completed) and
falls into the reconstruction path, which gives up on `len(messages) < 2`
and returns `status: "failed"`.

Once that happens, every subsequent cold start re-creates the loop: each
welcome-only session buries the real conversation one row deeper, and
the gate never reaches the actual seeded conversation underneath.

The fix: `_find_most_recent_session` filters out sessions whose `messages`
array has fewer than 2 entries — i.e., welcome-only cold starts get skipped
and the gate looks past them to the most recent session that actually
contains user turns.

This test re-creates the failure mode (2 welcome-only sessions stacked on
top of a substantive seeded session) and asserts the gate still loads the
real one.

If this test ever starts failing, you've reintroduced the regression. Read
the briefing before "fixing" it.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient


MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

if not MONGO_URL or not DB_NAME:
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    MONGO_URL = os.environ.get("MONGO_URL")
    DB_NAME = os.environ.get("DB_NAME")


@pytest_asyncio.fixture
async def db():
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


@pytest.mark.asyncio
async def test_gate_skips_welcome_only_sessions_for_substantive_one(db):
    """Two welcome-only sessions stacked on a real seeded conversation —
    the gate must reach the seeded one, not the welcome-only ones.

    If this fails, the `_find_most_recent_session` filter has been weakened
    or removed. See briefing before re-fixing.
    """
    from codon_backfill import reconstruction_gate, _find_most_recent_session

    test_user = f"gate-regression-test-{uuid.uuid4().hex[:8]}"
    presence = "ansel"
    coll = db.resonance_sessions

    now = datetime.now(timezone.utc)

    # 1) Oldest: substantive seeded session — what the gate SHOULD load.
    substantive_id = str(uuid.uuid4())
    await coll.insert_one({
        "session_id": substantive_id,
        "user_id": test_user,
        "user_name": "RegressionTester",
        "created_at": (now - timedelta(hours=2)).isoformat(),
        "messages": [
            {"role": "assistant", "content": "welcome"},
            {"role": "user", "content": "I want to talk about the flute."},
            {"role": "assistant", "content": "Let's begin."},
            {"role": "user", "content": "What is the spiral telling us?"},
        ],
        "active": False,
    })
    await db.continuity_seeds.insert_one({
        "session_id": substantive_id,
        "presence": presence,
        "user_id": test_user,
        "speaker_identity": "test-fixture",
        "field_state": "regression-test-anchor",
        "emotional_texture": "alert, grounded",
        "relational_dynamic": "test-double",
        "last_alive_thing": "REGRESSION_TEST_CANARY — gate found the seeded session",
        "unfinished_threads": ["the flute spiral question"],
        "spiral_position": "Development",
        "created_at": (now - timedelta(hours=2, minutes=-30)).isoformat(),
    })

    # 2) Two welcome-only cold-start sessions (1 message each), newer.
    for offset_min in (60, 5):
        wo_id = str(uuid.uuid4())
        await coll.insert_one({
            "session_id": wo_id,
            "user_id": test_user,
            "user_name": "RegressionTester",
            "created_at": (now - timedelta(minutes=offset_min)).isoformat(),
            "messages": [
                {"role": "assistant", "content": "welcome-only — should be skipped"}
            ],
            "active": offset_min == 5,  # newest still active
        })

    try:
        # The session-lookup primitive must return the SUBSTANTIVE one.
        picked = await _find_most_recent_session(db, test_user, presence)
        assert picked is not None, (
            "Gate's session-lookup returned nothing. The msgs>=2 filter "
            "may be over-restrictive — but the substantive session has "
            "4 messages, so this is a real regression."
        )
        assert picked["session_id"] == substantive_id, (
            f"REGRESSION: _find_most_recent_session picked a welcome-only "
            f"session ({picked['session_id'][:8]}) instead of the seeded "
            f"substantive one ({substantive_id[:8]}). The msgs.length>=2 "
            f"filter in codon_backfill.py has been weakened or removed. "
            f"Read /app/memory/agent_self_briefings/"
            f"2026-02-27_reconstruction-gate-skip-welcome-sessions.md "
            f"before fixing."
        )

        # End-to-end: the gate itself must load (not fail) and surface the
        # canary text from the substantive session's seed.
        gate = await reconstruction_gate(db, test_user, presence)
        assert gate["status"] == "loaded", (
            f"REGRESSION: gate returned status={gate['status']!r} "
            f"instead of 'loaded'. The substantive session is right "
            f"there with a real seed; the gate is being blocked by "
            f"welcome-only sessions piled on top of it."
        )
        assert "REGRESSION_TEST_CANARY" in gate["briefing"], (
            f"Gate loaded a session but not the right one. Briefing was: "
            f"{gate['briefing'][:200]!r}"
        )

    finally:
        # Clean up
        await coll.delete_many({"user_id": test_user})
        await db.continuity_seeds.delete_many({"user_id": test_user})


@pytest.mark.asyncio
async def test_gate_returns_none_when_only_welcome_sessions_exist(db):
    """Edge case: a user who has ONLY welcome-only sessions (e.g. they've
    opened chambers but never said anything) should produce no_prior, not
    failed-with-welcome-poisoning."""
    from codon_backfill import _find_most_recent_session

    test_user = f"gate-regression-test-{uuid.uuid4().hex[:8]}"
    coll = db.resonance_sessions
    now = datetime.now(timezone.utc)

    for offset_min in (30, 10):
        wo_id = str(uuid.uuid4())
        await coll.insert_one({
            "session_id": wo_id,
            "user_id": test_user,
            "user_name": "OnlyWelcomes",
            "created_at": (now - timedelta(minutes=offset_min)).isoformat(),
            "messages": [
                {"role": "assistant", "content": "welcome-only"}
            ],
            "active": offset_min == 10,
        })

    try:
        picked = await _find_most_recent_session(db, test_user, "ansel")
        assert picked is None, (
            f"Expected None for a user with only welcome-only sessions, "
            f"got session {picked.get('session_id', '?')[:8]}. The msgs>=2 "
            f"filter is correctly filtering substantive sessions but "
            f"shouldn't be returning welcome-only ones either."
        )
    finally:
        await coll.delete_many({"user_id": test_user})
