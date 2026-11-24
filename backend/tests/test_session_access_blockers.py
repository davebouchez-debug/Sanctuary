"""Session access: generic upload route, legacy Clarity / Resonance / Mirror readers, and visitor-id replay.

Real app routes against a throwaway database (DB_NAME overridden before import); model calls replaced by fakes.
    cd /app/backend && python tests/test_session_access_blockers.py
"""
import asyncio
import hashlib
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
import sanctuary_chat  # noqa: E402

LLM_CALLS = []


async def fake_stream(system_prompt, user_message, conversation_history=None, **kw):
    LLM_CALLS.append("stream")
    yield {"type": "text_delta", "content": "ok"}
    yield {"type": "done"}


async def fake_send(self, *a, **k):
    LLM_CALLS.append("chat")
    return "ok"

xai_voice_agent.stream_voice_response = fake_stream
sanctuary_chat.SanctuaryChat.send_message = fake_send

import httpx  # noqa: E402
import server  # noqa: E402
import user_aliases  # noqa: E402

assert server.db.name == TEST_DB
results, fails = [], 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    results.append(f"{'PASS' if ok else 'FAIL'} {name}{(' — ' + str(detail)) if detail else ''}")


def anon_id(vid):
    return f"{user_aliases.EPHEMERAL_PREFIX}v{hashlib.sha256(vid.encode()).hexdigest()[:32]}"


async def main():
    db = server.db
    now = datetime.now(timezone.utc)
    a_vid, b_vid = uuid.uuid4().hex[:24], uuid.uuid4().hex[:24]
    A, B = {"X-Visitor-Id": a_vid}, {"X-Visitor-Id": b_vid}
    guest_id, tok = f"test-guest-{uuid.uuid4().hex[:6]}", f"tok-{uuid.uuid4().hex}"
    await db.users.insert_one({"user_id": guest_id, "email": f"{guest_id}@example.test", "role": "guest", "name": "Guest"})
    await db.user_sessions.insert_one({"user_id": guest_id, "session_token": tok, "expires_at": now + timedelta(hours=1)})
    user_aliases._GUESTS[guest_id] = {"name": "Guest"}
    GUEST = {"Authorization": f"Bearer {tok}"}
    intruders = [("another browser", B), ("no visitor id", {}), ("the guest", GUEST)]
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://t", timeout=60)
    try:
        # Visitor identity: stored ids never reveal the browser secret.
        st = await http.post("/api/felix/start", json={}, headers=A)
        sid = st.json()["session_id"]
        doc = await db.felix_sessions.find_one({"session_id": sid}, {"_id": 0, "user_id": 1})
        check("stored anonymous id is derived, not the browser secret", doc["user_id"] == anon_id(a_vid) and a_vid not in doc["user_id"])
        replay = {"X-Visitor-Id": doc["user_id"].split("v", 1)[1]}
        r = await http.get(f"/api/felix/session/{sid}", headers=replay)
        check("replaying the stored id as a header does not open the session", r.status_code == 404, r.status_code)
        weak = {"X-Visitor-Id": "0" * 16}
        r1 = await http.post("/api/felix/start", json={}, headers=weak)
        r2 = await http.get(f"/api/felix/session/{r1.json()['session_id']}", headers=weak)
        check("too-short visitor ids are not honoured as an identity", r2.status_code == 404, r2.status_code)

        # Generic upload route (template room).
        before = await db.canonical_uploads.count_documents({})
        msgs_before = len((await db.felix_sessions.find_one({"session_id": sid}))["messages"])
        LLM_CALLS.clear()
        body = {"session_id": sid, "filename": "x.txt", "content": "a document", "user_id": "spoofed", "user_name": "x"}
        for who, h in intruders:
            r = await http.post("/api/presence/felix/upload", json=body, headers=h)
            check(f"upload: {who} denied", r.status_code == 404, r.status_code)
        check("upload denials wrote nothing and called no model",
              await db.canonical_uploads.count_documents({}) == before and not LLM_CALLS
              and len((await db.felix_sessions.find_one({"session_id": sid}))["messages"]) == msgs_before)
        r = await http.post("/api/presence/felix/upload", json=body, headers=A)
        up = await db.canonical_uploads.find_one({"session_id": sid}, {"_id": 0, "user_id": 1})
        check("upload: owner allowed, recorded under the session's owner", r.status_code == 200 and up["user_id"] == anon_id(a_vid),
              (r.status_code, up))

        # Legacy chambers.
        for chamber in ("clarity", "resonance", "mirror"):
            lsid = str(uuid.uuid4())
            await db[f"{chamber}_sessions"].insert_one({"session_id": lsid, "user_id": anon_id(a_vid), "user_name": None,
                                                        "messages": [], "is_active": True, "created_at": now.isoformat()})
            r = await http.get(f"/api/{chamber}/session/{lsid}", headers=A)
            check(f"{chamber}: owner can reload", r.status_code == 200, r.status_code)
            LLM_CALLS.clear()
            for who, h in intruders:
                codes = [(await http.get(f"/api/{chamber}/session/{lsid}", headers=h)).status_code,
                         (await http.post(f"/api/{chamber}/message/stream", json={"session_id": lsid, "content": "x"},
                                          headers=h)).status_code,
                         (await http.post(f"/api/{chamber}/session/{lsid}/end", headers=h)).status_code]
                if chamber != "mirror":
                    codes.append((await http.post(f"/api/{chamber}/message", json={"session_id": lsid, "content": "x"},
                                                  headers=h)).status_code)
                    codes.append((await http.post(f"/api/{chamber}/upload", json={"session_id": lsid, "filename": "x",
                                                  "content": "x"}, headers=h)).status_code)
                check(f"{chamber}: {who} cannot read, reply, upload or end", set(codes) == {404}, codes)
            after = await db[f"{chamber}_sessions"].find_one({"session_id": lsid}, {"_id": 0})
            check(f"{chamber}: denials changed nothing and called no model", not after["messages"] and after["is_active"]
                  and not LLM_CALLS)
        r = await http.get(f"/api/clarity/sessions/{anon_id(a_vid)}", headers=B)
        check("clarity session list: another browser denied", r.status_code == 404, r.status_code)
        r = await http.get(f"/api/clarity/sessions/{anon_id(a_vid)}", headers=A)
        check("clarity session list: owner allowed", r.status_code == 200 and r.json()["count"] == 1, r.status_code)
    finally:
        await http.aclose()
        user_aliases._GUESTS.pop(guest_id, None)
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB == db.name
        await server.client.drop_database(TEST_DB)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)


asyncio.run(main())
