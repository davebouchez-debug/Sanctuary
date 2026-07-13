"""
Sanctuary 2.0 — Migration (a): move production data off `test_database`.

MongoDB cannot rename a database in place. This copies every collection from
the current source DB into a freshly named production DB, doc-by-doc, then
verifies counts match. The source is never modified and never dropped — you
drop it manually only after you've confirmed the new DB serves correctly and
updated DB_NAME in /app/backend/.env.

SAFE BY DEFAULT: runs a dry-run (reports what it *would* copy) unless you pass
--execute. Source is opened read-only in intent (we only .find() it).

Usage:
    # See the plan, touch nothing:
    python scripts/migrate_prod_db_off_test_database.py --target sanctuary_prod

    # Actually copy:
    python scripts/migrate_prod_db_off_test_database.py --target sanctuary_prod --execute

    # Then, once verified:
    #   1. Set DB_NAME=sanctuary_prod in /app/backend/.env
    #   2. sudo supervisorctl restart backend
    #   3. Re-run scripts/db_audit_for_sanctuary2.py to confirm parity
    #   4. Only then drop the old DB by hand if you wish.
"""
import argparse
import asyncio
import os
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BATCH = 500


async def list_collections(db):
    names = await db.list_collection_names()
    return sorted(n for n in names if not n.startswith("system."))


async def copy_collection(src_db, dst_db, name, execute):
    src = src_db[name]
    total = await src.count_documents({})
    if not execute:
        return total, 0  # planned, copied

    dst = dst_db[name]
    existing = await dst.count_documents({})
    if existing:
        # Idempotent-ish: skip a collection that already matches the source
        # count so a re-run after a partial failure doesn't double-insert.
        if existing == total:
            print(f"    [skip] {name}: target already has {existing} docs")
            return total, existing
        raise RuntimeError(
            f"target {name} has {existing} docs but source has {total}; "
            f"clear the target collection before re-running to avoid dupes."
        )

    copied = 0
    buffer = []
    cursor = src.find({})
    async for doc in cursor:
        buffer.append(doc)  # _id preserved as-is
        if len(buffer) >= BATCH:
            await dst.insert_many(buffer, ordered=False)
            copied += len(buffer)
            buffer = []
    if buffer:
        await dst.insert_many(buffer, ordered=False)
        copied += len(buffer)
    return total, copied


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="new production DB name")
    ap.add_argument("--source", default=os.environ["DB_NAME"],
                    help="source DB (default: current DB_NAME)")
    ap.add_argument("--execute", action="store_true",
                    help="actually copy (default: dry-run)")
    args = ap.parse_args()

    if args.target == args.source:
        raise SystemExit("target must differ from source")

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    src_db = client[args.source]
    dst_db = client[args.target]

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"=== Migration ({mode}): {args.source!r} -> {args.target!r} ===\n")

    collections = await list_collections(src_db)
    grand_src = grand_copied = 0
    for name in collections:
        planned, copied = await copy_collection(src_db, dst_db, name, args.execute)
        grand_src += planned
        grand_copied += copied
        tag = f"copied {copied}" if args.execute else f"would copy {planned}"
        print(f"    {name}: {planned} docs — {tag}")

    print(f"\n    Source total:  {grand_src}")
    if args.execute:
        # Verify parity per collection
        print("\n=== VERIFY ===")
        mismatches = 0
        for name in collections:
            s = await src_db[name].count_documents({})
            d = await dst_db[name].count_documents({})
            ok = "OK" if s == d else "MISMATCH"
            if s != d:
                mismatches += 1
            print(f"    {name}: src={s} dst={d} [{ok}]")
        print(f"\n    {'ALL COLLECTIONS MATCH ✅' if mismatches == 0 else f'{mismatches} MISMATCH(ES) ❌'}")
        print("\n    Next: update DB_NAME in .env, restart backend, re-run db_audit.")
    else:
        print("\n    Dry-run only. Re-run with --execute to copy.")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
