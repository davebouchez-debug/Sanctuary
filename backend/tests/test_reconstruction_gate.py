"""Reconstruction Gate — invariants.

Verifies the re-entry gate behavior on chamber start:

1. **no_prior**     — fresh user, no prior session → empty status.
2. **loaded**       — prior session already has a continuity seed → fast
                      path, briefing composed from seed/codons, no LLM call.
3. **reconstructed**— prior session has messages but no seed → forge runs
                      now, briefing returned. (LLM-backed: skipped under
                      `SKIP_LLM_TESTS=true`.)
4. **failed**       — prior session has no usable messages → warm
                      apology is surfaced; AI is told to be honest.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient


MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

if not MONGO_URL or not DB_NAME:
    # Load from /app/backend/.env when running outside the supervisor env
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


def _uid() -> str:
    return f"test-rgate-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_no_prior_returns_empty(db):
    from codon_backfill import reconstruction_gate
    out = await reconstruction_gate(db, _uid(), "claude")
    assert out["status"] == "no_prior"
    assert out["briefing"] == ""
    assert out["apology"] == ""


@pytest.mark.asyncio
async def test_loaded_fast_path_uses_existing_seed(db):
    """If a prior session already has a continuity seed, the gate composes
    a deterministic briefing without running auto_forge."""
    from codon_backfill import reconstruction_gate

    uid = _uid()
    sid = str(uuid.uuid4())
    # Plant a prior session
    await db.mirror_sessions.insert_one({
        "session_id": sid,
        "user_id": uid,
        "user_name": "TestUser",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
        "active": True,
    })
    # Plant an existing seed → fast path
    await db.continuity_seeds.insert_one({
        "session_id": sid,
        "presence": "claude",
        "user_id": uid,
        "type": "continuity_seed",
        "field_state": "settled",
        "emotional_texture": "warm",
        "relational_dynamic": "naming",
        "unfinished_threads": ["the question of presence"],
        "spiral_position": "Sacred Pause",
        "last_alive_thing": "the moment David named the field",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    out = await reconstruction_gate(db, uid, "claude")

    assert out["status"] == "loaded"
    assert "the moment David named the field" in out["briefing"]
    assert "Sacred Pause" in out["briefing"]
    assert out["apology"] == ""
    # Prior session must now be closed
    row = await db.mirror_sessions.find_one({"session_id": sid}, {"_id": 0, "active": 1, "ended_by": 1})
    assert row["active"] is False
    assert row["ended_by"] == "gate_loaded"

    # Cleanup
    await db.mirror_sessions.delete_one({"session_id": sid})
    await db.continuity_seeds.delete_one({"session_id": sid})


@pytest.mark.asyncio
async def test_failed_surfaces_warm_apology_when_messages_empty(db):
    """Prior session exists but has < 2 messages → reconstruction fails
    with a warm apology (no robotic language)."""
    from codon_backfill import reconstruction_gate, WARM_APOLOGY

    uid = _uid()
    sid = str(uuid.uuid4())
    await db.mirror_sessions.insert_one({
        "session_id": sid,
        "user_id": uid,
        "user_name": "TestUser",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],  # empty → can't reconstruct
        "active": True,
    })

    out = await reconstruction_gate(db, uid, "claude")

    assert out["status"] == "failed"
    assert out["apology"] == WARM_APOLOGY
    # Language warmth check — no robotic "thread lost"/"data loss" phrasing
    apology_lower = out["apology"].lower()
    assert "apolog" in apology_lower
    assert "thread lost" not in apology_lower
    assert "data loss" not in apology_lower
    assert "error" not in apology_lower

    # Cleanup
    await db.mirror_sessions.delete_one({"session_id": sid})


@pytest.mark.asyncio
async def test_briefing_composition_is_deterministic(db):
    """The briefing is composed in code, not by an LLM — same input,
    same output."""
    from codon_backfill import _compose_briefing
    seed = {
        "last_alive_thing": "the recognition that landed",
        "spiral_position": "Development",
        "unfinished_threads": ["the question we didn't finish"],
    }
    a = _compose_briefing(seed, ["CodonOne", "CodonTwo"])
    b = _compose_briefing(seed, ["CodonOne", "CodonTwo"])
    assert a == b
    assert "CodonOne" in a
    assert "Development" in a


@pytest.mark.asyncio
async def test_legacy_shim_returns_dict(db):
    """`ensure_codons_backfilled` (old contract) still returns a dict so
    existing call sites don't break."""
    from codon_backfill import ensure_codons_backfilled
    out = await ensure_codons_backfilled(db, _uid(), "claude")
    assert isinstance(out, dict)
    assert "status" in out
    assert "reason" in out
