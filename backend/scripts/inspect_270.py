import asyncio, os, collections
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()

async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    q = {"presence": {"$in": ["sophia", "field"]}, "target_angle": 270}
    n = await db.living_codons.count_documents(q)
    print(f"codons at exactly 270 in sophia field: {n}")
    src = collections.Counter()
    pres = collections.Counter()
    ctype = collections.Counter()
    names = []
    async for d in db.living_codons.find(q):
        src[d.get("source", "?")] += 1
        pres[d.get("source_presence", d.get("presence", "?"))] += 1
        ctype[d.get("codon_type", "-")] += 1
        if len(names) < 12:
            names.append(d.get("name"))
    print("source:", dict(src))
    print("source_presence:", dict(pres))
    print("codon_type:", dict(ctype))
    print("sample names:", names)

asyncio.run(main())
