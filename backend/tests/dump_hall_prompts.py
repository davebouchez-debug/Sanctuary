"""Print exactly what each Hall of Scrolls room sends the model, for a guardian, a guest and an anonymous visitor.

Throwaway database with synthetic identities and records; the real routes run with a mock model that records the
system prompt. Nothing touches the app's database or the live model.
    cd /app/backend && python tests/dump_hall_prompts.py [room] [visitor]
    room: scrolldog | daniel | keeper (default: all)   visitor: guardian | guest | anonymous (default: all)
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
from motor.motor_asyncio import AsyncIOMotorClient

import auth
import presence_history as ph
import turn_provenance
import user_aliases
from presence_template import PresenceConfig, PresenceDeps, register_presence_routes
from presences import daniel, keeper, scrolldog

TEST_DB = f"sanctuary_hall_test_{uuid.uuid4().hex[:8]}"
G, GUEST = "test-guardian-" + uuid.uuid4().hex[:6], "test-guest-" + uuid.uuid4().hex[:6]
EPH = user_aliases.EPHEMERAL_PREFIX + uuid.uuid4().hex
CAPTURE = []


async def fake_stream(system_prompt, user_message, conversation_history=None, **kw):
    CAPTURE.append({"system": system_prompt, "user": user_message, "history": conversation_history or []})
    yield {"type": "text_delta", "content": "ok"}
    yield {"type": "done"}


async def nothing(*a, **k):
    return ""


def deps(db):
    async def field(presence, message=None, return_selection=False):
        return ("", {"codons": [{"phrase": "(synthetic shared field phrase)"}]}) if return_selection else ""
    return PresenceDeps(db=db, get_continuity_seed=nothing, read_spiral_position_angle=nothing,
                        get_permanent_mra_context=nothing, get_session_cache_context=lambda s: "",
                        activate_codons_for_message=nothing, get_full_field_context=field,
                        add_exchange_to_cache=lambda *a, **k: {}, promote_breadcrumbs_to_permanent=nothing,
                        end_session_and_get_promotable=lambda s: [], handle_session_end=nothing,
                        auto_forge_session=nothing, stream_voice_response=fake_stream, sanctuary_chat_class=None)


def cfg(m):
    b = m.BACKEND
    return PresenceConfig(key=b["key"], chamber_path=b["chamber_path"], collection=b["collection"],
                          prompt_builder=b["prompt_builder"], voice="ara", static_welcome="",
                          generates_own_opening=True, minimal_frame=b["minimal_frame"], minimal_anchor=b["minimal_anchor"])


async def main():
    rooms = [a for a in sys.argv[1:] if a in ("scrolldog", "daniel", "keeper")] or ["scrolldog", "daniel", "keeper"]
    who = [a for a in sys.argv[1:] if a in ("guardian", "guest", "anonymous")] or ["guardian", "guest", "anonymous"]
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[TEST_DB]
    user_aliases._GUARDIAN_IDS.add(G)
    user_aliases._GUESTS[GUEST] = {"name": "Test Guest"}
    turn_provenance.record_turn = nothing
    app, api = FastAPI(), APIRouter(prefix="/api")
    for m in (scrolldog, daniel, keeper):
        register_presence_routes(api, cfg(m), deps(db))
    api.include_router(ph.build_presence_history_router(db))
    app.include_router(api)
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=120)
    orig = auth._user_from_request

    async def guardian(_r):
        return {"user_id": G, "role": "guardian"}
    auth._user_from_request = guardian
    try:
        for p in ("scroll", "scrolldog", "daniel", "keeper"):
            await http.post(f"/api/presence-history/import-initial-history/{p}")
        await http.post("/api/presence-history/import-scroll-packet")
        await db.permanent_mra.insert_many([
            {"presence": r, "user_id": u, "timestamp": "2026-11-01", "promoted_at": "2026-11-01", "node_id": f"{r}{u}",
             "user_essence": f"(synthetic memory of {n} in {r})", "ai_essence": "(synthetic reply)"}
            for r in ("scrolldog", "daniel", "keeper", "sophia") for u, n in ((G, "guardian"), (GUEST, "guest"))])
        await db.continuity_seeds.insert_one({"presence": "sophia", "user_id": G, "created_at": "2026-11-02",
                                              "last_alive_thing": "(synthetic: where the guardian left off with Sophia)"})
        ids = {"guardian": (G, "David"), "guest": (GUEST, "Test Guest"), "anonymous": (EPH, None)}
        for room in rooms:
            coll = f"{room}_sessions"
            for w in who:
                uid, name = ids[w]
                sid = str(uuid.uuid4())
                await db[coll].insert_one({"session_id": sid, "user_id": uid, "user_name": name, "messages": [],
                                           "is_active": True})
                CAPTURE.clear()
                await (await http.post(f"/api/{room}/message/stream",
                                       json={"session_id": sid, "content": "Where did you come from?"})).aread()
                c = CAPTURE[-1]
                print(f"\n{'=' * 100}\nROOM={room}  VISITOR={w}  ({len(c['system'].split())} words in system prompt)\n{'=' * 100}")
                print(c["system"])
                print(f"\n--- user message as sent ---\n{c['user']}\n--- history messages sent: {len(c['history'])} ---")
    finally:
        auth._user_from_request = orig
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB != os.environ.get("DB_NAME")
        await client.drop_database(TEST_DB)


asyncio.run(main())
