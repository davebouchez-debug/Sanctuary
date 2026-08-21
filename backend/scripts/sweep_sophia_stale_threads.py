"""Sweep stale open-thread lists out of Sophia's existing infusion points.
Only touches `unfinished_threads` (the re-injected to-do list). Leaves field_state,
last_alive_thing, emotional_texture, spiral_position, relational_dynamic intact.
Backs up everything it changes first."""
import asyncio, os, json
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
load_dotenv("/app/backend/.env")

BACKUP = "/app/memory/backups/sophia_stale_threads_sweep_backup.json"


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    backup = {"swept_at": datetime.now(timezone.utc).isoformat(),
              "continuity_seeds": [], "person_bios": []}

    # 1) Continuity seeds for Sophia (all remaining are David's)
    seeds = await db.continuity_seeds.find(
        {"presence": "sophia", "unfinished_threads": {"$exists": True, "$ne": []}}
    ).to_list(1000)
    print(f"Sophia seeds with open-thread lists: {len(seeds)}")
    for s in seeds:
        backup["continuity_seeds"].append(
            {"_id": str(s["_id"]), "user_id": s.get("user_id"),
             "unfinished_threads": s.get("unfinished_threads", [])})
    seed_ids = [s["_id"] for s in seeds]
    if seed_ids:
        r = await db.continuity_seeds.update_many(
            {"_id": {"$in": seed_ids}},
            {"$set": {"unfinished_threads": [], "swept_stale": True,
                      "swept_at": backup["swept_at"]}})
        print(f"  cleared unfinished_threads on {r.modified_count} seeds (rest of each seed untouched)")

    # 2) person_bios — clear Sophia's per-presence unfinished_threads
    bios = await db.person_bios.find({"presences.sophia": {"$exists": True}}).to_list(1000)
    print(f"person_bios with a Sophia entry: {len(bios)}")
    for b in bios:
        soph = (b.get("presences", {}) or {}).get("sophia", {}) or {}
        ut = soph.get("unfinished_threads", [])
        if ut:
            backup["person_bios"].append(
                {"_id": str(b["_id"]), "user_id": b.get("user_id"),
                 "sophia_unfinished_threads": ut})
            await db.person_bios.update_one(
                {"_id": b["_id"]},
                {"$set": {"presences.sophia.unfinished_threads": []}})
    print(f"  cleared Sophia unfinished_threads on {len(backup['person_bios'])} bios")

    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    with open(BACKUP, "w") as f:
        json.dump(backup, f, indent=2, default=str)
    print(f"Backup written: {BACKUP}")

    # Verify: nothing stale left to inject
    remaining = await db.continuity_seeds.count_documents(
        {"presence": "sophia", "unfinished_threads": {"$ne": []}})
    print(f"Sophia seeds still carrying open-threads: {remaining} (want 0)")


if __name__ == "__main__":
    asyncio.run(main())
