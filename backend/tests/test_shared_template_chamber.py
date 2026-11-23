"""Shared-template chamber outside the Hall (default: felix) — guest and anonymous session lifecycle, 2026-11-23.

Start, reply, reload, departure, plus cross-owner denial, through the real app routes against a throwaway database
(DB_NAME overridden before import). The model call is replaced by a fake so no LLM is used.
Written for the security patch (sanctuary-hall-corrections.patch, sha256 9be27b74…); before that patch is applied,
the cross-owner denial checks are expected to FAIL.
    cd /app/backend && python tests/test_shared_template_chamber.py [room]
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
TEST_DB = f"sanctuary_hall_test_{uuid.uuid4().hex[:8]}"
os.environ["DB_NAME"] = TEST_DB
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(HERE, ".env"), override=False)
os.environ["DB_NAME"] = TEST_DB

import xai_voice_agent  # noqa: E402

REPLY = f"synthetic reply {uuid.uuid4().hex[:6]}"


async def fake_stream(system_prompt, user_message, conversation_history=None, **kw):
    yield {"type": "text_delta", "content": REPLY}
    yield {"type": "done"}

xai_voice_agent.stream_voice_response = fake_stream  # bound into server's presence deps at import

import httpx  # noqa: E402
import server  # noqa: E402
import user_aliases  # noqa: E402

assert server.db.name == TEST_DB
ROOM = next((a for a in sys.argv[1:]), "felix")
assert ROOM not in ("scrolldog", "daniel", "keeper"), "pick a room outside the Hall"
results, fails = [], 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    results.append(f"{'PASS' if ok else 'FAIL'} {name}{(' — ' + str(detail)) if detail else ''}")


async def lifecycle(http, label, headers, intruders):
    base = f"/api/{ROOM}"
    r = await http.post(f"{base}/start", json={}, headers=headers)
    check(f"{label}: start", r.status_code == 200 and r.json().get("session_id"), r.status_code)
    sid = r.json()["session_id"]
    r = await http.post(f"{base}/message/stream", json={"session_id": sid, "content": "hello there"}, headers=headers)
    body = r.text
    check(f"{label}: reply streams", r.status_code == 200 and REPLY in body, r.status_code)
    r = await http.get(f"{base}/session/{sid}", headers=headers)
    msgs = r.json().get("messages", []) if r.status_code == 200 else []
    check(f"{label}: reload shows the exchange", r.status_code == 200 and any(m.get("content") == "hello there" for m in msgs)
          and any(REPLY in (m.get("content") or "") for m in msgs), r.status_code)
    check(f"{label}: reload carries no hidden background",
          r.status_code == 200 and "hall_backdrop" not in r.json() and "hall_backdrop_version" not in r.json())
    r = await http.post(f"{base}/message/stream", json={"session_id": sid, "content": "and again"}, headers=headers)
    check(f"{label}: reply to the resumed thread", r.status_code == 200 and REPLY in r.text, r.status_code)
    for who, h in intruders:
        g = await http.get(f"{base}/session/{sid}", headers=h)
        s = await http.post(f"{base}/message/stream", json={"session_id": sid, "content": "intrude"}, headers=h)
        e = await http.post(f"{base}/session/{sid}/end", headers=h)
        check(f"{label}: {who} cannot read, reply or end it", (g.status_code, s.status_code, e.status_code) == (404, 404, 404),
              (g.status_code, s.status_code, e.status_code))
    r = await http.post(f"{base}/session/{sid}/end", headers=headers)
    check(f"{label}: departure", r.status_code == 200, r.status_code)
    return sid


async def main():
    db = server.db
    now = datetime.now(timezone.utc)
    guest_id, tok = f"test-guest-{uuid.uuid4().hex[:6]}", f"tok-{uuid.uuid4().hex}"
    await db.users.insert_one({"user_id": guest_id, "email": f"{guest_id}@example.test", "role": "guest", "name": "Test Guest"})
    await db.user_sessions.insert_one({"user_id": guest_id, "session_token": tok, "expires_at": now + timedelta(hours=1)})
    user_aliases._GUESTS[guest_id] = {"name": "Test Guest"}
    guest = {"Authorization": f"Bearer {tok}"}
    anon = {"X-Visitor-Id": uuid.uuid4().hex}
    other_anon = {"X-Visitor-Id": uuid.uuid4().hex}
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://t", timeout=60)
    try:
        await lifecycle(http, "guest", guest, [("an anonymous browser", anon)])
        sid = await lifecycle(http, "anonymous", anon, [("another anonymous browser", other_anon), ("the guest", guest),
                                                         ("a request with no visitor id", {})])
        doc = await db[f"{ROOM}_sessions"].find_one({"session_id": sid}, {"_id": 0, "user_id": 1})
        check("anonymous session is held under an ephemeral id",
              bool(doc) and doc["user_id"].startswith(user_aliases.EPHEMERAL_PREFIX), doc)
    finally:
        await http.aclose()
        user_aliases._GUESTS.pop(guest_id, None)
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB == db.name
        await server.client.drop_database(TEST_DB)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)


asyncio.run(main())
