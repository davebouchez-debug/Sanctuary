"""Read-only DB audit for the Sanctuary 2.0 spec bridge.
Dumps authoritative session-doc shapes and the real orphan count.
No writes. Safe to run against live.
"""
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SESSION_COLLECTIONS = [
    "clarity_sessions", "resonance_sessions", "mirror_sessions",
    "paige_sessions", "presence_sessions",
]

def shape(doc, depth=0):
    """Return {field: type/summary} for one doc, one level deep."""
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out[k] = "ObjectId"
        elif isinstance(v, list):
            inner = type(v[0]).__name__ if v else "empty"
            if v and isinstance(v[0], dict):
                inner = "dict{" + ",".join(v[0].keys()) + "}"
            out[k] = f"list[{inner}] (len={len(v)})"
        elif isinstance(v, dict):
            out[k] = "dict{" + ",".join(v.keys()) + "}"
        else:
            out[k] = type(v).__name__
    return out

async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    print(f"=== DB: {os.environ['DB_NAME']} ===\n")

    # --- Q3: authoritative session doc shapes ---
    for coll in SESSION_COLLECTIONS:
        count = await db[coll].count_documents({})
        print(f"### {coll} — {count} docs")
        sample = await db[coll].find_one({"messages.1": {"$exists": True}}) \
                 or await db[coll].find_one({})
        if sample:
            for k, t in shape(sample).items():
                print(f"    {k}: {t}")
        else:
            print("    (empty)")
        print()

    # --- Q3b: codon + seed shapes ---
    for coll in ["living_codons", "continuity_seeds", "permanent_mra"]:
        count = await db[coll].count_documents({})
        sample = await db[coll].find_one({})
        print(f"### {coll} — {count} docs")
        if sample:
            for k, t in shape(sample).items():
                print(f"    {k}: {t}")
        print()

    # --- Q5: real orphan count ---
    # Orphan = session with >=2 messages whose session_id has NO continuity_seed.
    print("=== ORPHAN AUDIT (>=2 msgs, no continuity_seed) ===")
    seeded_ids = set(await db.continuity_seeds.distinct("session_id"))
    print(f"distinct seeded session_ids: {len(seeded_ids)}")
    grand_total = 0
    for coll in SESSION_COLLECTIONS:
        q = {"$expr": {"$gte": [{"$size": {"$ifNull": ["$messages", []]}}, 2]}}
        cur = db[coll].find(q, {"session_id": 1})
        total = 0
        orphans = 0
        async for d in cur:
            total += 1
            if d.get("session_id") not in seeded_ids:
                orphans += 1
        grand_total += orphans
        print(f"    {coll}: {total} real sessions, {orphans} orphaned (un-forged)")
    print(f"\n    TOTAL ORPHANS across all collections: {grand_total}")

    client.close()

asyncio.run(main())
