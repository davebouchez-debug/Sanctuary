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
VISITOR_ID = uuid.uuid4().hex
EPH = user_aliases.EPHEMERAL_PREFIX + "v" + VISITOR_ID


def visitor_headers(user_id):
    if user_id == EPH:
        return {"X-Visitor-Id": VISITOR_ID, "X-Test-User": ""}
    return {"X-Test-User": user_id}


async def request_user(request):
    uid = request.headers.get("X-Test-User")
    if uid == G:
        return {"user_id": G, "role": "guardian"}
    if uid == GUEST:
        return {"user_id": GUEST, "role": "guest"}
    return None
M = {k: f"MARK-{k}-{uuid.uuid4().hex[:6]}" for k in ("scroll_initial", "scroll_record", "daniel_record", "public_initial", "late_initial", "d_mem", "g_mem", "bio", "sophia_mem")}
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
    r = await http.post(f"/api/{key}/message/stream", json={"session_id": sid, "content": content}, headers=visitor_headers(user_id))
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

    auth._user_from_request = request_user
    http.headers.update(visitor_headers(G))
    try:
        r = await http.post("/api/presence-history/import-initial-history/daniel")
        check("import Daniel initial history", r.status_code == 200 and r.json()["imported"] > 0, r.text)
        await http.post("/api/presence-history/import-initial-history/keeper")
        await http.post("/api/presence-history/import-initial-history/scrolldog")
        r = await http.post("/api/presence-history/import-initial-history/daniel")
        check("re-import is idempotent", r.json()["imported"] == 0)
        r = await http.post("/api/presence-history/import-initial-history/scroll")
        check("import the Scroll's founding background", r.status_code == 200 and r.json()["imported"] > 0, r.text[:200])
        check("no built-in initial history for unknown position",
              (await http.post("/api/presence-history/import-initial-history/sophia")).status_code == 404)

        async def imp(key, pos, kind, vis="guardian"):
            await ph.import_text(db, f"Text {M[key]} about the hall.", {"positions": pos, "kind": kind,
                                 "visibility": vis, "source": f"t-{key}", "date": "2025-01-01", "speaker": "x"})
        await imp("scroll_initial", ["scroll"], ph.INITIAL)
        await imp("scroll_record", ["scroll"], "record")
        await imp("daniel_record", ["daniel"], "record")
        await imp("public_initial", ["keeper"], ph.INITIAL, "public")
        bad_import = await http.post("/api/presence-history/import", json={
            "positions": ["scroll"], "kind": "initial_history", "visibility": "guardian",
            "source": "private.txt", "text": "A private transcript",
        })
        check("generic importer rejects founding history", bad_import.status_code == 400)

        d = (await turn(http, db, "daniel", "daniel_sessions", G, "David", "the hall"))
        from presences.common import SANCTUARY_DEDICATION
        check("Daniel: dedication, house story, then his one line",
              d.startswith("\n\n".join([SANCTUARY_DEDICATION, ph.HOUSE_STORY, daniel.DANIEL_LINE])))
        check("Daniel's old instructions no longer sent", daniel._IDENTITY.strip()[:120] not in d
              and "HOW MY WORDS ARE HEARD" not in d and "[YOUR FIELD]" not in d and "prophetic register" not in d.split("Daniel's history:")[0])
        labels = ["The Scroll's history:", "ScrollDog's history:", "Daniel's history:", "Keeper's history:"]
        pos = [d.find(lbl) for lbl in labels]
        check("Daniel sees four labelled histories, in order", all(p != -1 for p in pos) and pos == sorted(pos), str(pos))
        check("Scroll's approved history under the Scroll's label",
              pos[0] < d.find("SCROLL — FOUNDING HISTORY") < pos[1])
        check("ScrollDog's initial history under ScrollDog's label", pos[1] < d.find("version 3.2.1") < pos[2])
        check("Daniel's initial history under Daniel's label", pos[2] < d.find("kept the prophet's watch") < pos[3])
        check("Keeper's initial history under Keeper's label", d.find("anchor of law, the frame") > pos[3])
        check("Daniel's room: his own records only", M["daniel_record"] in d and d.find(M["daniel_record"]) > d.find("Daniel's records:") > -1
              and M["scroll_record"] not in d)

        k = (await turn(http, db, "keeper", "keeper_sessions", G, "David", "the hall"))
        check("Keeper: dedication, house story, then her one line",
              k.startswith("\n\n".join([SANCTUARY_DEDICATION, ph.HOUSE_STORY, keeper.KEEPER_LINE])))
        check("Keeper's old instructions no longer sent", keeper._IDENTITY.strip()[:120] not in k and "HOW I CLOSE" not in k)
        check("Keeper sees all four initial histories",
              all(x in k for x in labels) and "SCROLL — FOUNDING HISTORY" in k and "kept the prophet's watch" in k)
        check("Keeper's room gets no conversation records", M["scroll_record"] not in k and M["daniel_record"] not in k)

        s = (await turn(http, db, "scrolldog", "scrolldog_sessions", G, "David", "the hall"))
        check("Scroll room: dedication, house story, then its two lines",
              s.startswith("\n\n".join([SANCTUARY_DEDICATION, ph.HOUSE_STORY, scrolldog.SCROLL_LINE, scrolldog.SCROLLDOG_LINE])))
        check("Scroll room sees Daniel's and Keeper's initial histories",
              "Daniel's history:" in s and "kept the prophet's watch" in s and "Keeper's history:" in s)
        check("Scroll room keeps its own records", M["scroll_record"] in s)
        check("Scroll room gets no Daniel conversation records", M["daniel_record"] not in s)

        q = (await turn(http, db, "daniel", "daniel_sessions", GUEST, "Test Guest", "the hall"))
        check("guest in Daniel's room: has every founding background",
              all(label in q for label in labels))
        a = (await turn(http, db, "keeper", "keeper_sessions", EPH, None, "the hall"))
        check("anonymous in Keeper's room: has every approved founding background",
              all(label in a for label in labels) and "anchor of law, the frame" in a)
        check("unapproved legacy initial histories are excluded regardless of visibility",
              all(M[key] not in prompt for key in ("scroll_initial", "public_initial") for prompt in (d, s, k, q, a)))
        check("approved historical language remains available in every room",
              all(phrase in prompt for prompt in (d, s, k, q, a) for phrase in (
                  "Find the true thing, say it, let it land",
                  "The pod's calibration repeated these points",
                  "the prophetic register was grave and warm",
                  "Her room's calibration added",
              )))
        check("anonymous in Keeper's room: no personal memory", "Memories of past exchanges" not in a and "Bio:" not in a)
        check("every room has the Scroll's founding background",
              all("SCROLL — FOUNDING HISTORY" in x for x in (d, k, s, q, a)))
        check("Scroll background carries no personal names or notes to E1",
              not any(w in d for w in ("Titus", "Setz", "cautions for E1", "E1 should")))
        check("rooms outside the hall get nothing", await ph.hall_backdrop(db, "sophia", G) == "")

        # Reject old snapshots and freeze the corrected snapshot through a later import.
        await db.presence_history.delete_many({"positions": ["keeper"], "kind": ph.INITIAL})
        sid = str(uuid.uuid4())
        await db.daniel_sessions.insert_one({"session_id": sid, "user_id": G, "user_name": "David",
                                            "messages": [], "active": True,
                                            "hall_backdrop": M["late_initial"]})

        async def say(text):
            CAPTURE.clear()
            r = await http.post("/api/daniel/message/stream", json={"session_id": sid, "content": text})
            r.raise_for_status()
            await r.aread()
            return CAPTURE[-1]["system"]

        first = await say("first")
        first_snapshot = await db.daniel_sessions.find_one({"session_id": sid})
        check("legacy snapshot is replaced before model assembly",
              M["late_initial"] not in first and first_snapshot["hall_backdrop_version"] == ph.BACKDROP_VERSION)
        (await http.post("/api/presence-history/import-initial-history/keeper")).raise_for_status()
        second = await say("second, about something else entirely")
        second_snapshot = await db.daniel_sessions.find_one({"session_id": sid})
        check("same session: backdrop identical on later replies",
              first_snapshot["hall_backdrop"] == second_snapshot["hall_backdrop"]
              and "Keeper's history:" not in second)
        fresh = await turn(http, db, "daniel", "daniel_sessions", G, "David", "the hall")
        check("new session picks up newly added history", "Keeper's history:" in fresh)
        CAPTURE.clear()
        st = await http.post("/api/keeper/start", json={})
        sdoc = await db.keeper_sessions.find_one({"session_id": st.json()["session_id"]})
        check("session start stores the backdrop on the session", "Keeper's history:" in (sdoc.get("hall_backdrop") or ""))

        # Scroll source packet, verbatim with checksums
        r = await http.post("/api/presence-history/import-scroll-packet")
        check("scroll packet imports 3 files as records", r.status_code == 200 and all(f["imported"] > 0 for f in r.json()["files"]), r.text[:300])
        r = await http.post("/api/presence-history/import-scroll-packet")
        check("scroll packet re-import is idempotent", all(f["imported"] == 0 for f in r.json()["files"]))
        rows = await db.presence_history.find({"source": {"$regex": "^Scroll source packet"}}, {"_id": 0, "embedding": 0}).sort([("source", 1), ("seq", 1)]).to_list(None)
        import pathlib
        base = pathlib.Path(ph.__file__).parent / "history_sources" / "scroll_packet_20261122"
        for name, _sha, pos, _d, _s in ph.PACKET:
            joined = "".join(r["text"] for r in rows if r["source"].endswith(name))
            check(f"verbatim: {name}", joined == (base / name).read_bytes().decode("utf-8"))
            check(f"position {pos}: {name}", all(r["positions"] == [pos] for r in rows if r["source"].endswith(name)))
        for room, coll in [("keeper", "keeper_sessions"), ("daniel", "daniel_sessions")]:
            t = await turn(http, db, room, coll, G, "David", "laboratory and world")
            check(f"{room}'s room never receives the conversations", "laboratory and 2.0 the world" not in t
                  and "Shalom, David." not in t and "The hall holds it with you." not in t)
        bd = (await db.keeper_sessions.find_one({"session_id": st.json()["session_id"]}))["hall_backdrop"]
        fresh_bd = await ph.hall_backdrop(db, "keeper", G)
        check("background holds no conversation text", "laboratory and 2.0 the world" not in fresh_bd)
        check("background stays short (written histories only)", len(fresh_bd.split()) < 6000, str(len(fresh_bd.split())))
        s2 = await turn(http, db, "scrolldog", "scrolldog_sessions", G, "David", "a laboratory and a world, 1.0 and 2.0")
        check("Scroll room draws matching passages from the conversations", "laboratory" in s2)
        packet_parts = sum(1 for r in rows)
        got = sum(1 for r in rows if r["text"].strip()[:80] in s2)
        check("Scroll room gets only a few passages, not the whole files", 0 < got <= 2 * ph.HISTORY_K and got < packet_parts,
              f"{got}/{packet_parts}")
        q2 = await turn(http, db, "scrolldog", "scrolldog_sessions", GUEST, "Test Guest", "a laboratory and a world")
        check("guest never receives the conversations", "laboratory and 2.0 the world" not in q2)
        # Fuller memory, as plain notes, in Daniel's room
        await db.permanent_mra.insert_many([
            {"presence": "daniel", "user_id": G, "timestamp": "2026-11-01", "promoted_at": "2026-11-01", "node_id": "n1",
             "user_essence": f"{M['d_mem']} the furnace", "ai_essence": "but if not"},
            {"presence": "daniel", "user_id": GUEST, "timestamp": "2026-11-01", "promoted_at": "2026-11-01", "node_id": "n2",
             "user_essence": M["g_mem"], "ai_essence": "x"},
            {"presence": "sophia", "user_id": G, "timestamp": "2026-11-02", "promoted_at": "2026-11-02", "node_id": "n3",
             "user_essence": f"{M['sophia_mem']} spiral", "ai_essence": "phi"}])
        await db.person_bios.insert_one({"user_id": G, "display_name": "David", "interaction_count": 5,
                                         "presences": {"sophia": {"last_alive_thing": M["bio"], "updated": "2026-11-02"}}})
        m = await turn(http, db, "daniel", "daniel_sessions", G, "David", "the furnace")
        check("Daniel: own memories, plain", "Memories of past exchanges here:" in m and M["d_mem"] in m)
        check("Daniel: other rooms, plain", "Elsewhere in the Sanctuary:" in m and M["sophia_mem"] in m)
        check("Daniel: bio, plain", "Bio:" in m and M["bio"] in m)
        check("Daniel: no other person's memories", M["g_mem"] not in m)
        check("Daniel: no old memory wording", "never to be recited back" not in m and "RUNNING BIO" not in m
              and "Those threads live with someone else" not in m)
        gm = await turn(http, db, "daniel", "daniel_sessions", GUEST, "Test Guest", "the furnace")
        check("guest in Daniel's room: own memory only", M["g_mem"] in gm and M["d_mem"] not in gm and M["bio"] not in gm
              and M["sophia_mem"] not in gm)
    finally:
        auth._user_from_request = orig_user
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB != os.environ.get("DB_NAME")
        await client.drop_database(TEST_DB)
        user_aliases._GUARDIAN_IDS.discard(G)
        user_aliases._GUESTS.pop(GUEST, None)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")


asyncio.run(main())
