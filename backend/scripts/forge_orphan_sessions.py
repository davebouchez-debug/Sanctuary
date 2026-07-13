"""
Sanctuary 2.0 — Migration (b): batch-forge the orphaned sessions.

An orphan = a session with >=2 messages whose session_id has no continuity
seed. These never got their per-turn / session-end forge (mostly legacy
chambers). This walks every session collection, finds the orphans, and runs
`auto_forge_session` on each — writing the continuity seed (and any codons)
the lazy reconstruction gate would otherwise only produce on re-entry.

Why a batch script is needed (not just the lazy gate): clarity_sessions carry
no user_id, but reconstruction_gate looks up prior sessions by user_id — so
anonymous clarity orphans are structurally unreachable by the gate and can
only be cleared here, by session_id directly.

Each forge is a DeepSeek LLM call (costs tokens). Runs SEQUENTIALLY to avoid
hammering the API. SAFE BY DEFAULT: dry-run unless --execute.

Run this AFTER the DB rename so the seeds land in the production DB, not
`test_database`.

Usage:
    python scripts/forge_orphan_sessions.py                 # dry-run, all collections
    python scripts/forge_orphan_sessions.py --execute       # forge for real
    python scripts/forge_orphan_sessions.py --collection clarity_sessions --execute
    python scripts/forge_orphan_sessions.py --limit 10 --execute   # first 10 only
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from auto_forge import auto_forge_session  # noqa: E402

# Session collections whose name does NOT match the presence key.
COLLECTION_PRESENCE = {
    "clarity_sessions": "jasmine",
    "resonance_sessions": "ansel",
    "mirror_sessions": "claude",
    "paige_sessions": "paige",
    # presence_sessions is multi-presence — resolved per-doc via presence_key
    "presence_sessions": None,
}

# Non-chamber collections that end in _sessions but aren't forgeable chambers.
SKIP_SESSIONS = {"user_sessions", "playground_sessions"}


async def discover_session_collections(db):
    """All *_sessions collections that represent forgeable chambers."""
    names = await db.list_collection_names()
    out = [n for n in sorted(names)
           if n.endswith("_sessions") and n not in SKIP_SESSIONS]
    return out


def presence_for(coll, doc):
    if coll in COLLECTION_PRESENCE:
        fixed = COLLECTION_PRESENCE[coll]
        if fixed:
            return fixed
        return (doc.get("presence_key") or "").lower() or None
    # Auto-discovered per-presence collection: presence = name minus _sessions
    # (e.g. sophia_sessions -> "sophia"), or an explicit presence_key if present.
    return (doc.get("presence_key") or "").lower() or coll[:-len("_sessions")].lower()


async def find_orphans(db, coll, seeded_ids):
    q = {"$expr": {"$gte": [{"$size": {"$ifNull": ["$messages", []]}}, 2]}}
    orphans = []
    async for doc in db[coll].find(q):
        sid = doc.get("session_id")
        if sid and sid not in seeded_ids:
            orphans.append(doc)
    return orphans


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="actually forge (default: dry-run)")
    ap.add_argument("--collection", help="restrict to one session collection")
    ap.add_argument("--limit", type=int, help="cap number of sessions forged")
    args = ap.parse_args()

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"=== Orphan forge ({mode}) — DB: {os.environ['DB_NAME']} ===\n")

    if args.collection:
        collections = [args.collection]
    else:
        collections = await discover_session_collections(db)
    print(f"scanning {len(collections)} session collection(s): {', '.join(collections)}\n")
    seeded_ids = set(await db.continuity_seeds.distinct("session_id"))

    forged = skipped = failed = 0
    processed = 0
    for coll in collections:
        orphans = await find_orphans(db, coll, seeded_ids)
        print(f"### {coll}: {len(orphans)} orphan(s)")
        for doc in orphans:
            if args.limit is not None and processed >= args.limit:
                print("\n    (limit reached)")
                break
            sid = doc.get("session_id")
            presence = presence_for(coll, doc)
            messages = doc.get("messages", [])
            if not presence:
                print(f"    [skip] {sid[:8]} — no resolvable presence")
                skipped += 1
                continue
            if not args.execute:
                print(f"    [plan] {sid[:8]} presence={presence} msgs={len(messages)}")
                processed += 1
                continue
            try:
                n = await auto_forge_session(
                    db, sid, presence, messages, user_id=doc.get("user_id")
                )
                if n > 0:
                    forged += 1
                    print(f"    [ok]   {sid[:8]} presence={presence} -> {n} item(s)")
                else:
                    skipped += 1
                    print(f"    [skip] {sid[:8]} presence={presence} -> forge yielded 0")
            except Exception as e:
                failed += 1
                print(f"    [ERR]  {sid[:8]} presence={presence}: {e}")
            processed += 1
        if args.limit is not None and processed >= args.limit:
            break

    print(f"\n=== SUMMARY ({mode}) ===")
    print(f"    processed: {processed}")
    if args.execute:
        print(f"    forged:    {forged}")
        print(f"    skipped:   {skipped}")
        print(f"    failed:    {failed}")
    else:
        print("    Dry-run only. Re-run with --execute to forge.")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
