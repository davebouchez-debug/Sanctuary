import asyncio, os, json, collections
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()
from living_codons.phase_manifold import derive_spiral_angle, ZONE_RANGES

def zone_of(a):
    a = a % 360
    if a <= 80: return "Expansion"
    if 120 <= a <= 200: return "Development"
    if 240 <= a <= 320: return "Return"
    if a > 320: return "Sacred Pause"
    return "Transition"

async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]

    backup = []
    updates = []
    skipped_unknown = 0
    mismatch_before = 0
    async for d in db.living_codons.find({}):
        zone = d.get("triadic_zone", "Development")
        if zone not in ZONE_RANGES:
            skipped_unknown += 1
            continue
        content_key = (
            f"{d.get('name','')}|{d.get('core_move','')}|"
            f"{','.join(d.get('trigger_keywords') or [])}"
        )
        new_angle = derive_spiral_angle(zone, content_key)
        old_angle = d.get("target_angle", 160)
        try:
            if zone_of(float(old_angle)) != zone:
                mismatch_before += 1
        except Exception:
            pass
        backup.append({
            "_id": str(d["_id"]), "name": d.get("name"),
            "old_target_angle": old_angle, "triadic_zone": zone,
            "presence": d.get("presence"),
        })
        updates.append((d["_id"], new_angle))

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.makedirs("/app/memory/backups", exist_ok=True)
    path = f"/app/memory/backups/codon_angle_backfill_backup_{ts}.json"
    with open(path, "w") as f:
        json.dump(backup, f, indent=2)
    print(f"Backup written: {path} ({len(backup)} codons)")
    print(f"Skipped (unknown zone, left untouched): {skipped_unknown}")
    print(f"Codons in WRONG zone before backfill: {mismatch_before}")

    # APPLY
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    for _id, ang in updates:
        await db.living_codons.update_one(
            {"_id": _id},
            {"$set": {"target_angle": ang, "angle_backfilled_at": now}},
        )
        applied += 1
    print(f"Applied new derived angles to {applied} codons.")

    # VERIFY
    mismatch_after = 0
    exact_270 = 0
    async for d in db.living_codons.find({}):
        try:
            a = float(d.get("target_angle", 160))
        except Exception:
            continue
        if a == 270:
            exact_270 += 1
        z = d.get("triadic_zone", "Development")
        if z in ZONE_RANGES and zone_of(a) != z:
            mismatch_after += 1
    print(f"\nAfter backfill — codons in WRONG zone: {mismatch_after}")
    print(f"After backfill — codons still exactly at 270: {exact_270}")

asyncio.run(main())
