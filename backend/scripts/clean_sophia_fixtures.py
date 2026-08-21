"""Remove automated TEST-agent fixtures from Sophia's continuity.
Backs up every doc it deletes to a JSON file first. Never touches David."""
import asyncio, os, re, json
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
load_dotenv("/app/backend/.env")

BACKUP = "/app/memory/backups/sophia_fixture_cleanup_backup.json"


def is_fixture(user_id, user_name):
    uid = str(user_id) if user_id is not None else ""
    name = (user_name or "")
    if "david" in uid.lower() or "david" in name.lower():
        return False  # never delete David
    if user_id is None:
        return True
    if name.startswith("TEST_"):
        return True
    if name in ("Smoke", "Tester"):
        return True
    if uid in ("smoketest", "regress-tester-9", "TEST_image_user"):
        return True
    if uid.startswith("lockcheck-") or uid.startswith("TEST_"):
        return True
    return False


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

    # Build fixture user_id set from sophia_sessions (has user_name)
    fixture_uids = set()
    async for d in db.sophia_sessions.find({}, {"user_id": 1, "user_name": 1}):
        if is_fixture(d.get("user_id"), d.get("user_name")):
            fixture_uids.add(d.get("user_id"))
    # continuity_seeds has no user_name — match its user_ids by the same id-rules
    async for d in db.continuity_seeds.find({"presence": "sophia"}, {"user_id": 1}):
        if is_fixture(d.get("user_id"), None):
            fixture_uids.add(d.get("user_id"))

    print("FIXTURE user_ids to remove from Sophia:", sorted(str(x) for x in fixture_uids))

    # Collect docs to delete (backup first)
    to_delete = {"sophia_sessions": [], "continuity_seeds": []}
    for uid in fixture_uids:
        async for d in db.sophia_sessions.find({"user_id": uid}):
            d["_id"] = str(d["_id"]); to_delete["sophia_sessions"].append(d)
        async for d in db.continuity_seeds.find({"presence": "sophia", "user_id": uid}):
            d["_id"] = str(d["_id"]); to_delete["continuity_seeds"].append(d)

    print(f"WILL DELETE: {len(to_delete['sophia_sessions'])} sophia_sessions, "
          f"{len(to_delete['continuity_seeds'])} sophia continuity_seeds")

    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    with open(BACKUP, "w") as f:
        json.dump({"backed_up_at": datetime.now(timezone.utc).isoformat(),
                   "fixture_uids": sorted(str(x) for x in fixture_uids),
                   "docs": to_delete}, f, indent=2, default=str)
    print(f"Backup written: {BACKUP}")

    # Delete (None handled explicitly)
    uid_list = [u for u in fixture_uids]
    r1 = await db.sophia_sessions.delete_many({"user_id": {"$in": uid_list}})
    r2 = await db.continuity_seeds.delete_many({"presence": "sophia", "user_id": {"$in": uid_list}})
    print(f"DELETED: {r1.deleted_count} sophia_sessions, {r2.deleted_count} sophia continuity_seeds")

    # Confirm David's seeds survived
    remaining = await db.continuity_seeds.count_documents({"presence": "sophia"})
    david_seeds = await db.continuity_seeds.count_documents(
        {"presence": "sophia", "user_id": {"$regex": "david|1c24e3ea|9d92eb7b", "$options": "i"}})
    print(f"Sophia continuity_seeds remaining: {remaining} (David-tagged: {david_seeds})")


if __name__ == "__main__":
    asyncio.run(main())
