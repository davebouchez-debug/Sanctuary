"""One-off, reversible scrub (2026-11-02): E1's Milton test leftovers + David's eye-movement items.
Backup written to /app/memory/backups/eye_scrub_2026-11-02/backup.json before anything is deleted."""
import asyncio
import os
import re
from pathlib import Path

from bson import json_util
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
OUT = Path("/app/memory/backups/eye_scrub_2026-11-02")
EYE = re.compile(r"eye[- ]?(movement|access|position)|accessing cue", re.I)
DAVID_SESSION = "9b6976af-c3e9-4e22-b20a-0728359ccdb9"
COLLS = ["living_codons", "continuity_seeds", "permanent_mra", "turn_provenance"]


async def main():
    test_sids = await db.milton_sessions.distinct("session_id", {"user_id": {"$regex": "^qa-milton"}})
    test_sids.append("20adb527-13e0-4991-9b7d-95d86a88f50c")
    by_session = {"$or": [{"source_session": {"$in": test_sids}}, {"session_id": {"$in": test_sids}},
                          {"user_id": {"$regex": "^qa-milton"}}]}
    backup = {"deleted": {}, "edited": []}

    backup["deleted"]["milton_sessions"] = await db.milton_sessions.find({"session_id": {"$in": test_sids}}).to_list(None)
    for c in COLLS:
        backup["deleted"][c] = await db[c].find(by_session).to_list(None)

    # David's session: delete the eye-movement codon; trim only the eye line from his continuity seeds
    david_codons = [d async for d in db.living_codons.find({"source_session": DAVID_SESSION}) if EYE.search(str(d))]
    backup["deleted"]["living_codons"] += david_codons
    async for seed in db.continuity_seeds.find({"session_id": DAVID_SESSION}):
        threads = seed.get("unfinished_threads") or []
        kept = [t for t in threads if not EYE.search(str(t))]
        if len(kept) != len(threads) or (EYE.search(str(seed)) and threads == kept):
            backup["edited"].append({"collection": "continuity_seeds", "original": seed, "new_unfinished_threads": kept})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "backup.json").write_text(json_util.dumps(backup, indent=2))

    await db.milton_sessions.delete_many({"session_id": {"$in": test_sids}})
    for c in COLLS:
        await db[c].delete_many(by_session)
    await db.living_codons.delete_many({"_id": {"$in": [d["_id"] for d in david_codons]}})
    for e in backup["edited"]:
        await db.continuity_seeds.update_one({"_id": e["original"]["_id"]},
                                             {"$set": {"unfinished_threads": e["new_unfinished_threads"]}})

    print({k: len(v) for k, v in backup["deleted"].items()}, "seeds edited:", len(backup["edited"]))


async def restore():
    backup = json_util.loads((OUT / "backup.json").read_text())
    for c, docs in backup["deleted"].items():
        for d in docs:
            await db[c].replace_one({"_id": d["_id"]}, d, upsert=True)
    for e in backup["edited"]:
        await db.continuity_seeds.replace_one({"_id": e["original"]["_id"]}, e["original"], upsert=True)
    print("restored")


if __name__ == "__main__":
    import sys
    asyncio.run(restore() if "--restore" in sys.argv else main())
