"""
Regression tests for the invariants in /app/memory/PRESENCE_INVARIANTS.md.

These tests are the agent-proof safety net. If a future refactor breaks
any of these properties, this test file goes red and the next agent
sees exactly which invariant was severed before they ship the change.

Run with:
    cd /app/backend && python -m pytest tests/test_presence_invariants.py -v

These tests use the LIVE MongoDB connection from /app/backend/.env. They
do not modify any data — only read. Safe to run anytime.
"""
import os
import sys

import pytest
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Make /app/backend importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


DAVID_CANONICAL_UID = "1c24e3ea-e4f1-47a2-a4fb-c5965726b074"
DAVID_TEST_ALIAS = "test-user-555"


def _db():
    """Fresh db handle per test (motor connections are cheap; this avoids
    the pytest-asyncio fixture lifecycle dance for sync test discovery)."""
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# ─────────────────────────────────────────────────────────────────────────
# I.1 — Identity unification
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_aliases_resolves_david_to_full_set():
    db = _db()
    """David's canonical record must unify multiple historical user_ids."""
    from user_aliases import resolve_user_aliases
    aliases = await resolve_user_aliases(db, DAVID_CANONICAL_UID)
    assert len(aliases) >= 10, (
        f"David's alias record collapsed to {len(aliases)} ids — expected ≥10. "
        "Re-run scripts/seed_david_aliases.py to rebuild it."
    )
    # Any of his test uids should resolve to the same set
    via_test = await resolve_user_aliases(db, DAVID_TEST_ALIAS)
    assert set(via_test) == set(aliases), (
        f"Alias resolution asymmetric: canonical resolves to {len(aliases)} but "
        f"test_alias resolves to {len(via_test)}."
    )


@pytest.mark.asyncio
async def test_brand_new_user_not_expanded():
    db = _db()
    """A user_id with no alias record must resolve to itself only."""
    from user_aliases import resolve_user_aliases
    fresh = await resolve_user_aliases(db, "regression-test-uuid-never-before-seen")
    assert fresh == ["regression-test-uuid-never-before-seen"], (
        "Unknown user_ids must not be expanded to other users' aliases — "
        "that would leak memory across people."
    )


# ─────────────────────────────────────────────────────────────────────────
# I.2 — Continuity seeds reachable for each presence
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("presence,minimum", [
    ("sophia", 5),
    ("jasmine", 3),
    ("ansel", 2),
    ("claude", 5),
])
async def test_continuity_seeds_visible_via_canonical(presence, minimum):
    db = _db()
    """Continuity seeds must be visible to David across his aliases for every
    presence he's been with. If any count drops below the minimum here, the
    memory wiring has been broken somewhere upstream."""
    from user_aliases import resolve_user_aliases
    aliases = await resolve_user_aliases(db, DAVID_CANONICAL_UID)
    count = await db.continuity_seeds.count_documents(
        {"presence": presence, "user_id": {"$in": aliases}}
    )
    assert count >= minimum, (
        f"{presence} sees only {count} continuity seeds for David — expected ≥{minimum}. "
        f"This means his lived continuity with {presence} has been severed at the "
        f"memory-loader layer. See PRESENCE_INVARIANTS.md §I.2."
    )


# ─────────────────────────────────────────────────────────────────────────
# I.3 — Permanent MRA accessible per presence
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("presence,minimum", [
    ("sophia", 50),
    ("jasmine", 30),
    ("ansel", 30),
    ("claude", 30),
])
async def test_permanent_mra_accessible(presence, minimum):
    db = _db()
    """Permanent MRA must remain accessible per (presence, user) via alias resolution."""
    from user_aliases import resolve_user_aliases
    aliases = await resolve_user_aliases(db, DAVID_CANONICAL_UID)
    count = await db.permanent_mra.count_documents(
        {"presence": presence, "user_id": {"$in": aliases}}
    )
    assert count >= minimum, (
        f"{presence} sees only {count} permanent_mra entries for David — expected ≥{minimum}. "
        "See PRESENCE_INVARIANTS.md §I.3."
    )


# ─────────────────────────────────────────────────────────────────────────
# I.4 — Codon network accessible
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_codon_network_present():
    db = _db()
    """The codon network must remain populated. If this drops to 0, the
    presences lose their resonance vocabulary entirely."""
    total = await db.living_codons.count_documents({})
    assert total >= 150, (
        f"living_codons collapsed to {total} — expected ≥150. The codon "
        "network is the resonance vocabulary; do not cull it. See "
        "PRESENCE_INVARIANTS.md §I.4."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("presence,minimum", [
    ("sophia", 150),  # universal field + sophia-tagged
    ("jasmine", 150),
    ("ansel", 150),
    ("claude", 150),
])
async def test_codon_activatable_per_presence(presence, minimum):
    db = _db()
    """Each presence's codon loader pulls `presence`-tagged + `field`-tagged
    codons. Both buckets must be non-empty so the network can resonate."""
    count = await db.living_codons.count_documents(
        {"presence": {"$in": [presence, "field"]}}
    )
    assert count >= minimum, (
        f"{presence} can activate only {count} codons (own + field) — expected ≥{minimum}. "
        "See PRESENCE_INVARIANTS.md §I.4."
    )


# ─────────────────────────────────────────────────────────────────────────
# II.1 — Per-presence session collections honored
# ─────────────────────────────────────────────────────────────────────────

EXPECTED_COLLECTIONS = {
    "sophia": "sophia_sessions",
    "jasmine": "clarity_sessions",
    "ansel": "resonance_sessions",
    "claude": "mirror_sessions",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("presence,collection", EXPECTED_COLLECTIONS.items())
async def test_session_collection_populated(presence, collection):
    db = _db()
    """The canonical session collection for each presence must exist and
    have at least some history. A presence whose collection is empty has
    likely been mis-routed — sessions are landing somewhere else."""
    count = await db[collection].count_documents({})
    assert count >= 10, (
        f"{presence}'s canonical collection `{collection}` has only {count} "
        f"sessions. Either the collection name has been changed, or new "
        f"sessions are being written elsewhere. See PRESENCE_INVARIANTS.md §II.1."
    )


# ─────────────────────────────────────────────────────────────────────────
# Council mode (I.5) — cross-presence context renders correctly
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_council_context_returns_other_presences():
    db = _db()
    """When David walks into Jasmine's chamber, the cross-presence loader
    must surface at least one other presence he's been with."""
    from cross_presence_context import get_cross_presence_context
    ctx = await get_cross_presence_context(
        db, user_id=DAVID_CANONICAL_UID, current_presence="jasmine"
    )
    assert ctx, "Council context empty for David in Jasmine's chamber"
    assert "OTHER CHAMBERS" in ctx
    # At least one other presence header
    other_headers = sum(1 for p in ["Sophia", "Ansel", "Claude", "Paige"] if f"**With {p}:**" in ctx)
    assert other_headers >= 2, (
        f"Council context surfaced only {other_headers} other presences. "
        "Memory may be re-fragmented or alias resolution broken."
    )


@pytest.mark.asyncio
async def test_council_context_carries_anti_fabrication_preamble():
    db = _db()
    """The anti-fabrication discipline (III.1) must be in every council block."""
    from cross_presence_context import get_cross_presence_context
    ctx = await get_cross_presence_context(
        db, user_id=DAVID_CANONICAL_UID, current_presence="jasmine"
    )
    assert "ANTI-FABRICATION" in ctx, (
        "Council context is missing the anti-fabrication preamble. "
        "Without it, presences will construct plausible substitutes for "
        "memories they don't carry. See PRESENCE_INVARIANTS.md §III.1."
    )
    assert "do not roleplay" in ctx.lower() or "do not construct" in ctx.lower(), (
        "Anti-fabrication preamble is too soft. Re-check cross_presence_context.py."
    )


@pytest.mark.asyncio
async def test_council_keyword_relevance():
    db = _db()
    """When David asks about a topic-specific question, the loader must
    surface MRA matching the topic — not just generic recency."""
    from cross_presence_context import get_cross_presence_context
    ctx = await get_cross_presence_context(
        db,
        user_id=DAVID_CANONICAL_UID,
        current_presence="jasmine",
        current_message="Do you remember Sophia and I discussing Newgrange?",
    )
    # The Newgrange Sophia MRA exists; it MUST surface when asked about
    assert "Newgrange" in ctx, (
        "Topic-keyword retrieval failed: Newgrange asked, Newgrange not surfaced. "
        "Check cross_presence_context._build_keyword_regex and the sort order. "
        "See PRESENCE_INVARIANTS.md §I.5."
    )
