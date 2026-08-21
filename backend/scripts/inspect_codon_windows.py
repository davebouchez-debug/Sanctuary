import asyncio, os, collections
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()

async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    # Sophia's field = her own + "field"
    q = {"presence": {"$in": ["sophia", "field"]}}
    total = await db.living_codons.count_documents(q)
    print(f"Sophia field codons (sophia + field): {total}")

    has_window = 0
    has_kw = 0
    angles = collections.Counter()
    sample_fields = collections.Counter()
    async for d in db.living_codons.find(q):
        for k in d.keys():
            sample_fields[k] += 1
        if d.get("angular_window_half") is not None:
            has_window += 1
        kw = d.get("trigger_keywords") or []
        if kw:
            has_kw += 1
        ta = d.get("target_angle", 160)
        try:
            angles[round(float(ta))] += 1
        except Exception:
            angles["?"] += 1

    print(f"docs with per-codon angular_window_half: {has_window}/{total}")
    print(f"docs with trigger_keywords: {has_kw}/{total}")
    print("\ntarget_angle distribution:")
    for ang, n in sorted(angles.items(), key=lambda x: -x[1]):
        print(f"  {ang:>4}°  -> {n}")
    print("\nfields present across docs (name -> count):")
    for f, n in sample_fields.most_common():
        print(f"  {f}: {n}")

asyncio.run(main())
