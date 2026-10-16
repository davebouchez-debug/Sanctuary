"""Conversation threads: list / soft-delete / reopen (session_id) / new_thread / forge ledger.

Seeds sessions directly into Mongo (user_id prefixed qa-threads-) so most checks
need no LLM calls; one real end-to-end flow on Ansel (resonance) uses DeepSeek.
Run: cd /app/backend && python -m pytest tests/test_threads.py -v
"""
import os
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient
from dotenv import dotenv_values

API = os.environ.get("REACT_APP_BACKEND_URL")
if not API:
    API = dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL")
BASE = f"{API.rstrip('/')}/api"
_benv = dotenv_values("/app/backend/.env")
mdb = MongoClient(_benv["MONGO_URL"])[_benv["DB_NAME"]]
T = 120
NAME = "QA Threads Tester"
CREATED = []  # (collection, session_id) for report/cleanup


def _uid():
    return f"qa-threads-{uuid.uuid4().hex[:8]}"


def _iso(dt):
    return dt.isoformat()


def seed(collection, user_id, texts, active=True, age_hours=0.0, ended=False,
         deleted=False, extra=None):
    now = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    sid = f"qa-thr-{uuid.uuid4().hex[:12]}"
    msgs = []
    for i, t in enumerate(texts):
        msgs.append({"id": str(uuid.uuid4()), "role": "user" if i % 2 == 0 else "assistant",
                     "content": t, "timestamp": _iso(now - timedelta(minutes=len(texts) - i))})
    doc = {"session_id": sid, "id": sid, "user_id": user_id, "user_name": NAME,
           "created_at": _iso(now - timedelta(minutes=30)), "active": active, "messages": msgs}
    if ended:
        doc["ended_at"] = _iso(now)
    if deleted:
        doc["deleted"] = True
    doc.update(extra or {})
    mdb[collection].insert_one(doc)
    CREATED.append((collection, sid))
    return sid


# presence -> (collection, start url, extra)
PRESENCES = {
    "ansel": ("resonance_sessions", "/resonance/start", {}),
    "claude": ("mirror_sessions", "/mirror/start", {}),
    "jasmine": ("clarity_sessions", "/clarity/start", {}),
    "louis_lot": ("louis_lot_sessions", "/louis-lot/start", {}),
    "sophia": ("sophia_sessions", "/spiral/start", {}),
    "kalahar": ("kalahar_sessions", "/kalahar/start", {}),
    "elowen": ("presence_sessions", "/presence/elowen/chat/start", {"presence_key": "elowen"}),
}


# --- Listing ---
@pytest.mark.parametrize("presence", list(PRESENCES))
def test_list_threads_filters_and_orders(presence):
    coll, _, extra = PRESENCES[presence]
    uid = _uid()
    old = seed(coll, uid, ["Old thread about gardens and roses", "reply"], age_hours=5, active=False, extra=extra)
    new = seed(coll, uid, ["one two three four five six seven eight nine ten", "reply", "more"], extra=extra)
    seed(coll, uid, ["welcome only"], extra=extra)  # 1 message -> excluded
    seed(coll, uid, ["deleted thread", "r"], deleted=True, extra=extra)  # deleted -> excluded
    seed(coll, _uid(), ["someone else", "r"], extra=extra)  # other user -> excluded
    r = requests.get(f"{BASE}/threads/{presence}", params={"user_id": uid}, timeout=T)
    assert r.status_code == 200
    th = r.json()["threads"]
    assert [t["session_id"] for t in th] == [new, old]
    assert th[0]["title"] == "one two three four five six seven eight…"
    assert th[1]["title"] == "Old thread about gardens and roses"
    assert th[0]["message_count"] == 3 and th[0]["active"] is True
    assert th[1]["active"] is False
    for t in th:
        assert t["created_at"] and t["last_activity"]


def test_list_threads_unknown_user_empty():
    r = requests.get(f"{BASE}/threads/ansel", params={"user_id": _uid()}, timeout=T)
    assert r.status_code == 200 and r.json()["threads"] == []


# --- Soft delete ---
@pytest.mark.parametrize("presence", ["ansel", "louis_lot", "elowen"])
def test_soft_delete(presence):
    coll, _, extra = PRESENCES[presence]
    uid = _uid()
    sid = seed(coll, uid, ["delete me please", "ok"], extra=extra)
    # other user's delete -> 404
    r = requests.delete(f"{BASE}/threads/{presence}/{sid}", params={"user_id": _uid()}, timeout=T)
    assert r.status_code == 404
    r = requests.delete(f"{BASE}/threads/{presence}/{sid}", params={"user_id": uid}, timeout=T)
    assert r.status_code == 200 and r.json()["deleted"] is True
    doc = mdb[coll].find_one({"session_id": sid})
    assert doc["deleted"] is True and doc["active"] is False  # still recoverable
    th = requests.get(f"{BASE}/threads/{presence}", params={"user_id": uid}, timeout=T).json()["threads"]
    assert sid not in [t["session_id"] for t in th]
    # deleted thread cannot be reopened
    _, url, _ = PRESENCES[presence]
    s = requests.post(f"{BASE}{url}", json={"user_id": uid, "user_name": NAME, "session_id": sid}, timeout=T).json()
    CREATED.append((coll, s["session_id"]))
    assert s["session_id"] != sid and not s.get("resumed")


def test_delete_nonexistent_404():
    r = requests.delete(f"{BASE}/threads/ansel/nope-{uuid.uuid4().hex}", params={"user_id": _uid()}, timeout=T)
    assert r.status_code == 404


# --- Reopen by session_id (ended, old) + forge ledger ---
@pytest.mark.parametrize("presence", list(PRESENCES))
def test_reopen_ended_old_thread(presence):
    coll, url, extra = PRESENCES[presence]
    uid = _uid()
    sid = seed(coll, uid, ["Reopen marker alpha", "reply", "second q", "reply2"], active=False,
               ended=True, age_hours=72, extra=extra)
    r = requests.post(f"{BASE}{url}", json={"user_id": uid, "user_name": NAME, "session_id": sid}, timeout=T)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["session_id"] == sid and d.get("resumed") is True
    assert len(d["messages"]) == 4 and d["messages"][0]["content"] == "Reopen marker alpha"
    doc = mdb[coll].find_one({"session_id": sid})
    assert doc["active"] is True and "ended_at" not in doc
    led = mdb["forge_ledger"].find_one({"session_id": sid})
    assert led and led["forged_count"] == 4


@pytest.mark.parametrize("presence", ["ansel", "louis_lot", "elowen"])
def test_reopen_other_users_thread_refused(presence):
    coll, url, extra = PRESENCES[presence]
    sid = seed(coll, _uid(), ["private stuff", "r"], extra=extra)
    d = requests.post(f"{BASE}{url}", json={"user_id": _uid(), "user_name": NAME, "session_id": sid}, timeout=T).json()
    CREATED.append((coll, d["session_id"]))
    assert d["session_id"] != sid and not d.get("resumed")


# --- Auto-resume (<2h) vs new_thread vs stale ---
@pytest.mark.parametrize("presence", ["ansel", "claude", "jasmine", "louis_lot", "elowen"])
def test_auto_resume_and_new_thread(presence):
    coll, url, extra = PRESENCES[presence]
    uid = _uid()
    sid = seed(coll, uid, ["recent thread", "r"], extra=extra)
    d = requests.post(f"{BASE}{url}", json={"user_id": uid, "user_name": NAME}, timeout=T).json()
    assert d["session_id"] == sid and d.get("resumed") is True
    d2 = requests.post(f"{BASE}{url}", json={"user_id": uid, "user_name": NAME, "new_thread": True}, timeout=T).json()
    CREATED.append((coll, d2["session_id"]))
    assert d2["session_id"] != sid and not d2.get("resumed")


def test_stale_thread_not_auto_resumed():
    coll, url, extra = PRESENCES["louis_lot"]
    uid = _uid()
    sid = seed(coll, uid, ["stale", "r"], age_hours=3, extra=extra)
    d = requests.post(f"{BASE}{url}", json={"user_id": uid, "user_name": NAME}, timeout=T).json()
    CREATED.append((coll, d["session_id"]))
    assert d["session_id"] != sid and not d.get("resumed")


# --- Forge ledger unit: re-ending must not re-forge ---
def test_claim_unforged_ledger():
    import sys
    sys.path.insert(0, "/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient
    from auto_forge import _claim_unforged

    async def run():
        db = AsyncIOMotorClient(_benv["MONGO_URL"])[_benv["DB_NAME"]]
        sid = f"qa-thr-ledger-{uuid.uuid4().hex[:8]}"
        msgs = [{"role": "user", "content": str(i)} for i in range(6)]
        a = await _claim_unforged(db, sid, msgs)
        b = await _claim_unforged(db, sid, msgs)  # same again -> nothing
        c = await _claim_unforged(db, sid, msgs + [{"role": "user", "content": "6"}, {"role": "assistant", "content": "7"}])
        await db["forge_ledger"].delete_one({"session_id": sid})
        return a, b, c
    a, b, c = asyncio.run(run())
    assert len(a) == 6 and b == []
    assert [m["content"] for m in c] == ["4", "5", "6", "7"]  # 2 msgs context + new part


# --- Real end-to-end on Ansel (DeepSeek) ---
def test_real_flow_resonance():
    uid = _uid()
    s1 = requests.post(f"{BASE}/resonance/start", json={"user_id": uid, "user_name": NAME, "new_thread": True}, timeout=T).json()
    sid1 = s1["session_id"]; CREATED.append(("resonance_sessions", sid1))
    r = requests.post(f"{BASE}/resonance/message", json={"session_id": sid1, "content": "QA threads test: my code word is heron."}, timeout=T)
    assert r.status_code == 200, r.text
    th = requests.get(f"{BASE}/threads/ansel", params={"user_id": uid}, timeout=T).json()["threads"]
    assert th and th[0]["session_id"] == sid1 and th[0]["title"].startswith("QA threads test")
    s2 = requests.post(f"{BASE}/resonance/start", json={"user_id": uid, "user_name": NAME, "new_thread": True}, timeout=T).json()
    CREATED.append(("resonance_sessions", s2["session_id"]))
    assert s2["session_id"] != sid1
    end = requests.post(f"{BASE}/resonance/session/{sid1}/end", timeout=T)
    assert end.status_code == 200
    s3 = requests.post(f"{BASE}/resonance/start", json={"user_id": uid, "user_name": NAME, "session_id": sid1}, timeout=T).json()
    assert s3["session_id"] == sid1 and s3["resumed"] is True
    n_before = len(s3["messages"])
    assert any("heron" in m.get("content", "") for m in s3["messages"])
    r = requests.post(f"{BASE}/resonance/message", json={"session_id": sid1, "content": "What was my code word?"}, timeout=T)
    assert r.status_code == 200
    assert "heron" in r.json().get("response", {}).get("content", "").lower()
    doc = mdb.resonance_sessions.find_one({"session_id": sid1})
    assert len(doc["messages"]) == n_before + 2


def test_zz_print_created():
    print("\nCREATED_SESSIONS:", CREATED)
    with open("/app/test_reports/pytest/threads_created_sessions.txt", "a") as f:
        for c, s in CREATED:
            f.write(f"{c} {s}\n")
