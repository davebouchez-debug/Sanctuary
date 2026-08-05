"""READ-ONLY DB inspection for the Sanctuary 2.0 audit.
Lists collections, indexes, counts, and field SHAPES (keys + value types only).
Values are redacted — no personal content is printed. Nothing is written."""
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")


def shape(doc, prefix=""):
    out = {}
    for k, v in doc.items():
        if k == "_id":
            t = "ObjectId"
        elif isinstance(v, list):
            inner = type(v[0]).__name__ if v else "empty"
            t = f"list[{inner}]({len(v)})"
        elif isinstance(v, dict):
            t = f"dict(keys={list(v.keys())[:8]})"
        elif isinstance(v, str):
            t = f"str(len={len(v)})"
        else:
            t = type(v).__name__
        out[k] = t
    return out


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    print(f"DB_NAME = {os.environ['DB_NAME']}")
    names = await db.list_collection_names()
    print(f"\nCOLLECTIONS ({len(names)}): {sorted(names)}\n")
    print("=" * 70)
    for name in sorted(names):
        coll = db[name]
        count = await coll.count_documents({})
        idx = await coll.index_information()
        idx_keys = {k: v.get("key") for k, v in idx.items()}
        print(f"\n[{name}]  docs={count}")
        print(f"  indexes: {idx_keys}")
        sample = await coll.find_one({}, sort=[("_id", -1)])
        if sample:
            print(f"  shape:   {shape(sample)}")
        # distinct user_id / presence footprint where relevant
        try:
            if "user_id" in (sample or {}):
                uids = await coll.distinct("user_id")
                print(f"  distinct user_id count: {len(uids)}")
            if "presence" in (sample or {}):
                pres = await coll.distinct("presence")
                print(f"  distinct presence: {sorted([str(p) for p in pres])[:30]}")
        except Exception as e:
            print(f"  (distinct probe skipped: {e})")
    print("\n" + "=" * 70)
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
