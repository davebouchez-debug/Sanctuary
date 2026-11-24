"""Interrupted founding-history imports recover, and incomplete histories are never frozen into a Hall session.

Throwaway database; the real ScrollDog routes run with a mock model.
    cd /app/backend && python tests/test_founding_import_recovery.py
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
import httpx
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

import auth
import presence_history as ph
import turn_provenance
import user_aliases
from presence_template import PresenceConfig, PresenceDeps, register_presence_routes
from presences import daniel, scrolldog

TEST_DB = f"sanctuary_hall_test_{uuid.uuid4().hex[:8]}"
G = "test-guardian-" + uuid.uuid4().hex[:6]
results, fails, CAPTURE = [], 0, []


def check(name, ok, detail=""):
    global fails
    fails += not ok
    results.append(f"{'PASS' if ok else 'FAIL'} {name}{(' — ' + str(detail)) if detail else ''}")


async def fake_stream(system_prompt, user_message, conversation_history=None, **kw):
    CAPTURE.append(system_prompt)
    yield {"type": "text_delta", "content": "ok"}
    yield {"type": "done"}


async def nothing(*a, **k):
    return ""


def deps(db):
    async def field(presence, message=None, return_selection=False):
        return ("", {"codons": []}) if return_selection else ""
    return PresenceDeps(db=db, get_continuity_seed=nothing, read_spiral_position_angle=nothing,
                        get_permanent_mra_context=nothing, get_session_cache_context=lambda s: "",
                        activate_codons_for_message=nothing, get_full_field_context=field,
                        add_exchange_to_cache=lambda *a, **k: {}, promote_breadcrumbs_to_permanent=nothing,
                        end_session_and_get_promotable=lambda s: [], handle_session_end=nothing,
                        auto_forge_session=nothing, stream_voice_response=fake_stream, sanctuary_chat_class=None)


def interrupted_insert(keep):
    original = AsyncIOMotorCollection.insert_many

    async def partial(self, docs, *a, **k):
        docs = list(docs)
        await original(self, docs[:keep], *a, **k)
        raise RuntimeError("simulated interruption")
    return original, partial


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[TEST_DB]
    user_aliases._GUARDIAN_IDS.add(G)
    turn_provenance.record_turn = nothing
    app, api = FastAPI(), APIRouter(prefix="/api")
    b = scrolldog.BACKEND
    register_presence_routes(api, PresenceConfig(
        key=b["key"], chamber_path=b["chamber_path"], collection=b["collection"], prompt_builder=b["prompt_builder"],
        voice="ara", static_welcome="", generates_own_opening=True, minimal_frame=b["minimal_frame"],
        minimal_anchor=b["minimal_anchor"]), deps(db))
    api.include_router(ph.build_presence_history_router(db))
    app.include_router(api)
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=120)
    orig_user = auth._user_from_request

    async def guardian(_r):
        return {"user_id": G, "role": "guardian"}
    auth._user_from_request = guardian
    coll = db[ph.COLLECTION]
    try:
        for p in ("scroll", "scrolldog", "keeper"):
            await http.post(f"/api/presence-history/import-initial-history/{p}")
        # Daniel's founding history is interrupted after one part is written.
        original, partial = interrupted_insert(1)
        AsyncIOMotorCollection.insert_many = partial
        try:
            r = await http.post("/api/presence-history/import-initial-history/daniel")
            check("interrupted import surfaces an error", r.status_code >= 500, r.status_code)
        except Exception as e:  # ASGITransport may re-raise the app error
            check("interrupted import surfaces an error", "simulated interruption" in str(e), e)
        finally:
            AsyncIOMotorCollection.insert_many = original
        rows = await coll.find({"positions": ["daniel"], "kind": ph.INITIAL}, {"_id": 0, "seq": 1, "of": 1}).to_list(None)
        check("partial copy left behind", len(rows) == 1 and rows[0]["of"] > 1, rows)
        text, complete = await ph.hall_backdrop_state(db, "daniel", None)
        check("incomplete history is not offered as complete", not complete and "Daniel's history:" not in text)

        # A session started while incomplete is not frozen.
        st = await http.post("/api/scrolldog/start", json={})
        sid = st.json()["session_id"]
        doc = await db.scrolldog_sessions.find_one({"session_id": sid})
        check("session start does not freeze an incomplete background",
              "hall_backdrop_version" not in doc and "hall_backdrop" not in doc)
        CAPTURE.clear()
        await (await http.post("/api/scrolldog/message/stream", json={"session_id": sid, "content": "hello"})).aread()
        doc = await db.scrolldog_sessions.find_one({"session_id": sid})
        check("a turn while incomplete does not freeze it either", "hall_backdrop_version" not in doc)
        check("that turn carries no partial Daniel history", "Daniel's history:" not in CAPTURE[-1]
              and "kept the prophet's watch" not in CAPTURE[-1])

        # Re-running the import recovers it in full, without duplicates.
        r = await http.post("/api/presence-history/import-initial-history/daniel")
        check("re-import recovers the interrupted history", r.status_code == 200 and r.json()["imported"] > 1, r.text[:200])
        rows = await coll.find({"positions": ["daniel"], "kind": ph.INITIAL}, {"_id": 0, "seq": 1, "of": 1}).to_list(None)
        check("no duplicate or stray parts", len(rows) == rows[0]["of"] and {x["seq"] for x in rows} == set(range(rows[0]["of"])))
        r = await http.post("/api/presence-history/import-initial-history/daniel")
        check("complete import stays idempotent", r.json().get("imported") == 0)
        text, complete = await ph.hall_backdrop_state(db, "scrolldog", None)
        check("all four now complete", complete and daniel.INITIAL_HISTORY.split("\n\n")[1] in text)

        # The same session now freezes the complete background, and keeps it.
        CAPTURE.clear()
        await (await http.post("/api/scrolldog/message/stream", json={"session_id": sid, "content": "again"})).aread()
        doc = await db.scrolldog_sessions.find_one({"session_id": sid})
        check("next turn freezes the complete background", doc.get("hall_backdrop_version") == ph.BACKDROP_VERSION
              and "Daniel's history:" in doc.get("hall_backdrop", ""))
        check("that turn carries all four histories", all(x in CAPTURE[-1] for x in
              ("The Scroll's history:", "ScrollDog's history:", "Daniel's history:", "Keeper's history:")))
        st2 = await http.post("/api/scrolldog/start", json={})
        doc2 = await db.scrolldog_sessions.find_one({"session_id": st2.json()["session_id"]})
        check("a new session start freezes the complete background", doc2.get("hall_backdrop_version") == ph.BACKDROP_VERSION)

        # Record imports (the Scroll packet) recover the same way.
        original, partial = interrupted_insert(2)
        AsyncIOMotorCollection.insert_many = partial
        try:
            await http.post("/api/presence-history/import-scroll-packet")
        except Exception:
            pass
        finally:
            AsyncIOMotorCollection.insert_many = original
        r = await http.post("/api/presence-history/import-scroll-packet")
        check("packet re-import completes", r.status_code == 200, r.status_code)
        for name, _sha, _pos, _d, _s in ph.PACKET:
            rows = await coll.find({"source": f"Scroll source packet 2026-11-22: {name}"}, {"_id": 0, "seq": 1, "of": 1}).to_list(None)
            check(f"packet file complete, no duplicates: {name}",
                  rows and len(rows) == rows[0]["of"] and {x["seq"] for x in rows} == set(range(rows[0]["of"])))
    finally:
        auth._user_from_request = orig_user
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB != os.environ.get("DB_NAME")
        await client.drop_database(TEST_DB)
        user_aliases._GUARDIAN_IDS.discard(G)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)


asyncio.run(main())
