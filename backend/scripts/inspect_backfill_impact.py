import asyncio, os, collections
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()

async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    q = {"presence": {"$in": ["sophia", "field"]}}

    # For codons at the 270 clump: what zone do they claim?
    clump = collections.Counter()
    async for d in db.living_codons.find({**q, "target_angle": 270}):
        clump[d.get("triadic_zone", "?")] += 1
    print("Zone of the 220 codons stuck at 270:")
    for z, n in clump.most_common():
        print(f"  {z}: {n}")

    # Field-wide: does stored zone AGREE with stored angle's zone?
    def zone_of(a):
        a = a % 360
        if a <= 80: return "Expansion"
        if 120 <= a <= 200: return "Development"
        if 240 <= a <= 320: return "Return"
        if a > 320: return "Sacred Pause"
        return "Transition"

    agree = mismatch = 0
    zone_dist = collections.Counter()
    async for d in db.living_codons.find(q):
        z = d.get("triadic_zone", "Development")
        zone_dist[z] += 1
        try:
            a = float(d.get("target_angle", 160))
        except Exception:
            continue
        if zone_of(a) == z:
            agree += 1
        else:
            mismatch += 1
    print(f"\nStored angle currently matches stored zone: {agree}")
    print(f"Stored angle currently in WRONG zone:        {mismatch}")
    print("\nZone distribution across the whole field (this is what backfill preserves):")
    for z, n in zone_dist.most_common():
        print(f"  {z}: {n}")

asyncio.run(main())
