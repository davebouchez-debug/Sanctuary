"""
Seed David's canonical user_alias record.

Scans every collection that stores user_id+user_name pairs, collects all
distinct user_ids that have ever been associated with user_name == "David",
and writes one canonical record so memory loaders can unify them.

Idempotent — re-running just refreshes the alias list.
"""
import asyncio
import os
import sys

# Make /app/backend importable so we can use the existing user_aliases module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

from user_aliases import upsert_canonical

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


CANDIDATE_NAME = "David"

# Collections that store {user_id, user_name} for sessions/seeds/memory.
# We scan each and union the user_ids.
SCAN_TARGETS = [
    ("sophia_sessions", "user_id", "user_name"),
    ("mirror_sessions", "user_id", "user_name"),
    ("clarity_sessions", "user_id", "user_name"),
    ("resonance_sessions", "user_id", "user_name"),
    ("playground_sessions", "user_id", "user_name"),
    ("presence_sessions", "user_id", "user_name"),
]


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    found_ids = set()
    for collection, uid_field, name_field in SCAN_TARGETS:
        cursor = db[collection].find(
            {name_field: CANDIDATE_NAME, uid_field: {"$ne": None}},
            {uid_field: 1, "_id": 0},
        )
        async for doc in cursor:
            uid = doc.get(uid_field)
            if uid:
                found_ids.add(uid)

    # Also pull user_ids that show up in memory artifacts with user_name David
    # (continuity_seeds and permanent_mra don't store user_name, so they ride
    # along with the session_ids above).

    if not found_ids:
        print(f"No user_ids found for user_name='{CANDIDATE_NAME}'. Nothing to do.")
        return

    sorted_ids = sorted(found_ids)
    print(f"Found {len(sorted_ids)} historical user_ids for '{CANDIDATE_NAME}':")
    for uid in sorted_ids:
        print(f"  • {uid}")

    # Pick a stable canonical_id — prefer the one with the most session history
    # so it's the "real" one. Fall back to lexicographic first.
    best_uid = sorted_ids[0]
    best_count = -1
    for uid in sorted_ids:
        cnt = 0
        for collection, uid_field, _name in SCAN_TARGETS:
            cnt += await db[collection].count_documents({uid_field: uid})
        if cnt > best_count:
            best_count = cnt
            best_uid = uid

    aliases = [u for u in sorted_ids if u != best_uid]
    print()
    print(f"Canonical: {best_uid} ({best_count} total session records)")
    print(f"Aliases ({len(aliases)}): {aliases}")

    await upsert_canonical(
        db,
        canonical_id=best_uid,
        aliases=aliases,
        user_name=CANDIDATE_NAME,
        note=(
            "Auto-seeded by scripts/seed_david_aliases.py. Unifies every "
            "historical user_id that has been 'David' across all chamber "
            "sessions, so memory loaders see one continuous field instead of "
            "fragmented slices per browser/session."
        ),
    )

    print()
    print(f"✓ Canonical alias record written. David's accumulated field memory "
          f"is now visible to every presence regardless of which historical "
          f"user_id arrives in the current session.")


if __name__ == "__main__":
    asyncio.run(main())
