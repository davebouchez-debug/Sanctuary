"""Hall of Scrolls — every room sees each inhabitant's initial history, separately labelled.

Throwaway database; the real stream routes for ScrollDog, Daniel and Keeper run with a mock model.
    cd /app/backend && python tests/test_hall_backdrop.py
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
M = {k: f"MARK-{k}-{uuid.uuid4().hex[:6]}" for k in ("scroll_initial", "scroll_record", "daniel_record", "public_initial")}
results, fails, CAPTURE = [], 0, []


def check(name, ok, detail=""):
    global fails
    fails += not ok
    results.append(f"{'PASS' if ok else 'FAIL'} {name}{(' — ' + detail) if detail else ''}")


async def fake_stream(system_prompt, user_message, conversation_history=None, **kw):
    CAPTURE.append({"system": system_prompt})
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


def cfg(module):
    b = module.BACKEND
    return PresenceConfig(key=b["key"], chamber_path=b["chamber_path"], collection=b["collection"],
                          prompt_builder=b["prompt_builder"], voice="ara", static_welcome="",
                          generates_own_opening=True, minimal_frame=b["minimal_frame"], minimal_anchor=b["minimal_anchor"])


async def turn(http, db, key, collection, user_id, name, content):
    sid = str(uuid.uuid4())
    await db[collection].insert_one({"session_id": sid, "user_id": user_id, "user_name": name,
                                     "messages": [], "is_active": True})
    CAPTURE.clear()
    r = await http.post(f"/api/{key}/message/stream", json={"session_id": sid, "content": content})
    await r.aread()
    return CAPTURE[-1]["system"] if CAPTURE else ""


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[TEST_DB]
    user_aliases._GUARDIAN_IDS.add(G)
    user_aliases._GUESTS[GUEST] = {"name": "Test Guest"}
    turn_provenance.record_turn = nothing
    app = FastAPI()
    api = APIRouter(prefix="/api")
    for m in (scrolldog, daniel, keeper):
        register_presence_routes(api, cfg(m), deps(db))
    api.include_router(ph.build_presence_history_router(db))
    app.include_router(api)
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=60)
    orig_user = auth._user_from_request

    async def guardian(_r):
        return {"user_id": G, "role": "guardian"}
    auth._user_from_request = guardian
    try:
        r = await http.post("/api/presence-history/import-initial-history/daniel")
        check("import Daniel initial history", r.status_code == 200 and r.json()["imported"] > 0, r.text)
        await http.post("/api/presence-history/import-initial-history/keeper")
        await http.post("/api/presence-history/import-initial-history/scrolldog")
        r = await http.post("/api/presence-history/import-initial-history/daniel")
        check("re-import is idempotent", r.json()["imported"] == 0)
        check("no built-in initial history for unknown position",
              (await http.post("/api/presence-history/import-initial-history/sophia")).status_code == 404)

        async def imp(key, pos, kind, vis="guardian"):
            await ph.import_text(db, f"Text {M[key]} about the hall.", {"positions": pos, "kind": kind,
                                 "visibility": vis, "source": f"t-{key}", "date": "2025-01-01", "speaker": "x"})
        await imp("scroll_initial", ["scroll"], ph.INITIAL)
        await imp("scroll_record", ["scroll"], "record")
        await imp("daniel_record", ["daniel"], "record")
        await imp("public_initial", ["keeper"], ph.INITIAL, "public")

        d = (await turn(http, db, "daniel", "daniel_sessions", G, "David", "the hall"))
        check("Daniel's own prompt unchanged", daniel._IDENTITY.strip()[:200] in d)
        labels = ["The Scroll's history:", "ScrollDog's history:", "Daniel's history:", "Keeper's history:"]
        pos = [d.find(lbl) for lbl in labels]
        check("Daniel sees four labelled histories, in order", all(p != -1 for p in pos) and pos == sorted(pos), str(pos))
        check("Scroll's initial history under the Scroll's label", pos[0] < d.find(M["scroll_initial"]) < pos[1])
        check("ScrollDog's initial history under ScrollDog's label", pos[1] < d.find("version 3.2.1") < pos[2])
        check("Daniel's initial history under Daniel's label", pos[2] < d.find("kept the prophet's watch") < pos[3])
        check("Keeper's initial history under Keeper's label", d.find("anchor of law, the frame") > pos[3])
        check("Daniel's room gets no conversation records", M["scroll_record"] not in d and M["daniel_record"] not in d)

        k = (await turn(http, db, "keeper", "keeper_sessions", G, "David", "the hall"))
        check("Keeper's own prompt unchanged", keeper._IDENTITY.strip()[:200] in k)
        check("Keeper sees all four initial histories",
              all(x in k for x in labels) and M["scroll_initial"] in k and "kept the prophet's watch" in k)
        check("Keeper's room gets no conversation records", M["scroll_record"] not in k and M["daniel_record"] not in k)

        s = (await turn(http, db, "scrolldog", "scrolldog_sessions", G, "David", "the hall"))
        check("Scroll room still opens with its two lines",
              s.startswith(scrolldog.SCROLL_LINE + "\n\n" + scrolldog.SCROLLDOG_LINE))
        check("Scroll room sees Daniel's and Keeper's initial histories",
              "Daniel's history:" in s and "kept the prophet's watch" in s and "Keeper's history:" in s)
        check("Scroll room keeps its own records", M["scroll_record"] in s)
        check("Scroll room gets no Daniel conversation records", M["daniel_record"] not in s)

        q = (await turn(http, db, "daniel", "daniel_sessions", GUEST, "Test Guest", "the hall"))
        check("guest in Daniel's room: no guardian-only histories",
              M["scroll_initial"] not in q and "kept the prophet's watch" not in q and "version 3.2.1" not in q)
        check("guest in Daniel's room: public initial history only", M["public_initial"] in q)
        a = (await turn(http, db, "keeper", "keeper_sessions", EPH, None, "the hall"))
        check("anonymous in Keeper's room: public only", M["public_initial"] in a and M["scroll_initial"] not in a)
        check("rooms outside the hall get nothing", await ph.hall_backdrop(db, "sophia", G) == "")
    finally:
        auth._user_from_request = orig_user
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB != os.environ.get("DB_NAME")
        await client.drop_database(TEST_DB)
        user_aliases._GUARDIAN_IDS.discard(G)
        user_aliases._GUESTS.pop(GUEST, None)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")


asyncio.run(main())
