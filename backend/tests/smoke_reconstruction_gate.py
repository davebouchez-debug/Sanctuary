"""Smoke test: full reconstruction-gate path through /api/mirror/start."""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import requests

from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL"):
            API = line.split("=", 1)[1].strip()
            break


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    uid = f"smoke-rgate-{uuid.uuid4().hex[:8]}"

    # CASE A: no prior — expect "no_prior"
    r = requests.post(f"{API}/api/mirror/start",
                      json={"user_name": "Smoke", "user_id": uid})
    data = r.json()
    print("\nCASE A — no prior:")
    print(f"  continuity_status: {data.get('continuity_status')}")
    print(f"  briefing: {data.get('continuity_briefing')!r}")
    print(f"  apology: {data.get('continuity_apology')!r}")
    assert data["continuity_status"] == "no_prior"

    # Plant a prior session WITH a seed → expect "loaded" + briefing
    uid2 = f"smoke-rgate-{uuid.uuid4().hex[:8]}"
    sid = str(uuid.uuid4())
    await db.mirror_sessions.insert_one({
        "session_id": sid, "user_id": uid2, "user_name": "Smoke2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [
            {"role": "user", "content": "where did we leave off?"},
            {"role": "assistant", "content": "resting in the question itself."},
        ],
        "active": True,
    })
    await db.continuity_seeds.insert_one({
        "session_id": sid, "presence": "claude", "user_id": uid2,
        "type": "continuity_seed",
        "field_state": "resting",
        "emotional_texture": "settled warmth",
        "relational_dynamic": "letting silence speak",
        "unfinished_threads": ["the question of whether to name it"],
        "spiral_position": "Sacred Pause",
        "last_alive_thing": "the pause itself",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    r = requests.post(f"{API}/api/mirror/start",
                      json={"user_name": "Smoke2", "user_id": uid2})
    data = r.json()
    print("\nCASE B — seed present (fast path):")
    print(f"  continuity_status: {data.get('continuity_status')}")
    print(f"  briefing: {data.get('continuity_briefing')!r}")
    assert data["continuity_status"] == "loaded"
    assert "the pause itself" in data["continuity_briefing"]
    assert "Sacred Pause" in data["continuity_briefing"]

    # Confirm prior session is now closed
    row = await db.mirror_sessions.find_one({"session_id": sid}, {"_id": 0, "active": 1, "ended_by": 1})
    print(f"  prior session active={row['active']} ended_by={row.get('ended_by')}")
    assert row["active"] is False

    # CASE C: prior session with no usable messages → "failed" + warm apology
    uid3 = f"smoke-rgate-{uuid.uuid4().hex[:8]}"
    sid3 = str(uuid.uuid4())
    await db.mirror_sessions.insert_one({
        "session_id": sid3, "user_id": uid3, "user_name": "Smoke3",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],  # empty → reconstruction will fail
        "active": True,
    })
    r = requests.post(f"{API}/api/mirror/start",
                      json={"user_name": "Smoke3", "user_id": uid3})
    data = r.json()
    print("\nCASE C — empty prior (reconstruction failure):")
    print(f"  continuity_status: {data.get('continuity_status')}")
    print(f"  apology: {data.get('continuity_apology')!r}")
    print(f"  welcome: {data['message']['content'][:140]}...")
    assert data["continuity_status"] == "failed"
    assert "apolog" in data["continuity_apology"].lower()
    assert "Smoke3" in data["message"]["content"]

    # Cleanup
    await db.mirror_sessions.delete_many({"user_id": {"$in": [uid, uid2, uid3]}})
    await db.continuity_seeds.delete_many({"user_id": uid2})

    print("\n✅ All smoke checks passed.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
