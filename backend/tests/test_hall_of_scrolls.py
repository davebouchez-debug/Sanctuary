"""Hall of Scrolls (Scroll / ScrollDog) minimal frame + history — security and prompt tests.

Throwaway database, synthetic identities and records; the real stream route runs with a mock model that records
the exact system prompt and history it receives.
    cd /app/backend && python tests/test_hall_of_scrolls.py
"""
import asyncio
import os
import subprocess
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
from presences import scrolldog

TEST_DB = f"sanctuary_hall_test_{uuid.uuid4().hex[:8]}"
G, GUEST = "test-guardian-" + uuid.uuid4().hex[:6], "test-guest-" + uuid.uuid4().hex[:6]
VISITOR_ID = uuid.uuid4().hex
EPH = user_aliases.EPHEMERAL_PREFIX + "v" + VISITOR_ID


def visitor_headers(user_id):
    if user_id == EPH:
        return {"X-Visitor-Id": VISITOR_ID}
    return {"X-Test-User": user_id}


async def request_user(request):
    uid = request.headers.get("X-Test-User")
    if uid == G:
        return {"user_id": G, "role": "guardian"}
    if uid == GUEST:
        return {"user_id": GUEST, "role": "guest"}
    return None
M = {k: f"MARK-{k}-{uuid.uuid4().hex[:6]}" for k in
     ("scroll_only", "dog_only", "shared", "public", "signed_in", "field_state", "spiral", "texture",
      "alive", "guest_alive", "guest_mem", "other_presence")}
REMOVED = ["HOW MY WORDS ARE HEARD", "I'm here, in the Sanctuary",
           "never to be recited back", "This is who I am and where I already am", "You are not required to greet",
           "I greet", "has just crossed your threshold", "You can see it", "I'm ScrollDog. I manifest the scroll",
           "MANIFESTATION of the scroll", "[CONTINUITY", "[YOUR FIELD]", "Room to listen", "BARK is enforcement"]
results, fails = [], 0
CAPTURE = []


def check(name, ok, detail=""):
    global fails
    fails += not ok
    results.append(f"{'PASS' if ok else 'FAIL'} {name}{(' — ' + detail) if detail else ''}")


async def fake_stream(system_prompt, user_message, conversation_history=None, **kw):
    CAPTURE.append({"system": system_prompt, "user": user_message, "history": conversation_history or []})
    yield {"type": "text_delta", "content": "# Heading\n- **ok**"}
    yield {"type": "done"}


class FakeChat:
    def __init__(self, system_prompt=None, **kw):
        self.system_prompt = system_prompt

    async def send_message(self, msg):
        CAPTURE.append({"system": self.system_prompt, "user": msg, "history": []})
        return "Hello."


async def nothing(*a, **k):
    return ""


def deps(db):
    async def field(presence, message=None, return_selection=False):
        sel = {"codons": [{"phrase": "Synthetic shared phrase"}]}
        return ("[YOUR FIELD]\n\nThis is who I am and where I already am.\n\n• Synthetic shared phrase", sel) \
            if return_selection else ""
    return PresenceDeps(db=db, get_continuity_seed=nothing, read_spiral_position_angle=nothing,
                        get_permanent_mra_context=nothing, get_session_cache_context=lambda s: "",
                        activate_codons_for_message=nothing, get_full_field_context=field,
                        add_exchange_to_cache=lambda *a, **k: {}, promote_breadcrumbs_to_permanent=nothing,
                        end_session_and_get_promotable=lambda s: [], handle_session_end=nothing,
                        auto_forge_session=nothing, stream_voice_response=fake_stream, sanctuary_chat_class=FakeChat)


def cfg(module, minimal_frame):
    b = module.BACKEND
    return PresenceConfig(key=b["key"], chamber_path=b["chamber_path"], collection=b["collection"],
                          prompt_builder=b["prompt_builder"], voice="ara", static_welcome="",
                          generates_own_opening=True, minimal_frame=minimal_frame, minimal_anchor=b["minimal_anchor"])


async def turn(http, db, key, collection, user_id, name, content="hello", history=None):
    sid = str(uuid.uuid4())
    await db[collection].insert_one({"session_id": sid, "user_id": user_id, "user_name": name,
                                     "messages": history or [], "is_active": True})
    CAPTURE.clear()
    r = await http.post(f"/api/{key}/message/stream", json={"session_id": sid, "content": content}, headers=visitor_headers(user_id))
    await r.aread()
    return CAPTURE[-1] if CAPTURE else {"system": "", "user": "", "history": []}


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[TEST_DB]
    user_aliases._GUARDIAN_IDS.add(G)
    user_aliases._GUESTS[GUEST] = {"name": "Test Guest"}
    turn_provenance.record_turn = nothing
    app = FastAPI()
    api = APIRouter(prefix="/api")
    register_presence_routes(api, cfg(scrolldog, "always"), deps(db))
    api.include_router(ph.build_presence_history_router(db))
    app.include_router(api)
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=60)
    original_request_user = auth._user_from_request
    auth._user_from_request = request_user
    try:
        imp = lambda key, pos, vis="guardian": ph.import_text(db, f"Record text {M[key]} about the hall and the field.",
                                                               {"positions": pos, "kind": "record", "visibility": vis,
                                                                "source": f"test-{key}", "date": "2025-04-13",
                                                                "speaker": "David and the Scroll"})
        for key, pos, vis in [("scroll_only", ["scroll"], "guardian"), ("dog_only", ["scrolldog"], "guardian"),
                              ("shared", ["scroll", "scrolldog"], "guardian"), ("public", ["scroll"], "public"),
                              ("signed_in", ["scroll"], "signed_in")]:
            await imp(key, pos, vis)
        check("re-import is idempotent", (await imp("shared", ["scroll", "scrolldog"]))["imported"] == 0)
        await db.continuity_seeds.insert_many([
            {"presence": "scrolldog", "user_id": G, "created_at": "2026-11-20", "field_state": M["field_state"],
             "spiral_position": M["spiral"], "emotional_texture": M["texture"], "last_alive_thing": M["alive"],
             "unfinished_threads": ["the next scroll"], "speaker_identity": "turn_cessation"},
            {"presence": "scrolldog", "user_id": GUEST, "created_at": "2026-11-20", "last_alive_thing": M["guest_alive"]},
            {"presence": "keeper", "user_id": G, "created_at": "2026-11-20", "last_alive_thing": M["other_presence"]}])
        await db.permanent_mra.insert_one({"presence": "scrolldog", "user_id": GUEST, "timestamp": "2026-11-20",
                                           "user_essence": M["guest_mem"], "ai_essence": "x"})

        H = ("scrolldog", "scrolldog_sessions")
        g = await turn(http, db, *H, G, "David", "tell me about the hall and the field")
        sysg = g["system"]
        from presences.common import SANCTUARY_DEDICATION
        check("prompt order: dedication, house story, then the two lines",
              sysg.startswith("\n\n".join([SANCTUARY_DEDICATION, ph.HOUSE_STORY, scrolldog.SCROLL_LINE, scrolldog.SCROLLDOG_LINE])))
        check("signed-in fact present", "David is here, signed in." in sysg)
        sc, dg = sysg.find("The Scroll's records:"), sysg.find("ScrollDog's records:")
        check("both histories present and labelled", sc != -1 and dg != -1)
        check("Scroll-only record under the Scroll's history", sc < sysg.find(M["scroll_only"]) < dg)
        check("ScrollDog-only record under ScrollDog's history", sysg.find(M["dog_only"]) > dg)
        check("guardian receives every record (nothing hidden from either)",
              all(M[k] in sysg for k in ("scroll_only", "dog_only", "shared", "public", "signed_in")))
        check("continuity: allowed fields supplied", M["alive"] in sysg and "the next scroll" in sysg)
        check("continuity: operational fields never supplied",
              not any(M[k] in sysg for k in ("field_state", "spiral", "texture")) and "turn_cessation" not in sysg)
        check("other person's notes and memories absent", M["guest_alive"] not in sysg and M["guest_mem"] not in sysg)
        el = sysg.find("Elsewhere in the Sanctuary:")
        check("other room's notes appear only under 'Elsewhere', for the same person",
              el != -1 and sysg.find(M["other_presence"]) > el and sysg.find("With Keeper:") > el)
        check("shared field phrases plain-labelled", "Shared field phrases:\n- Synthetic shared phrase" in sysg)
        bad = [p for p in REMOVED if p in sysg]
        check("no inherited or behavioural text in prompt", not bad, ", ".join(bad))
        check("user message carries no injected framing", g["user"] == "tell me about the hall and the field")

        q = await turn(http, db, *H, GUEST, "Test Guest", "the hall and the field")
        check("signed-in guest gets no guardian records",
              not any(M[k] in q["system"] for k in ("scroll_only", "shared", "dog_only")))
        check("signed-in guest gets signed_in + public records", M["signed_in"] in q["system"] and M["public"] in q["system"])
        check("guest sees own continuity only", M["guest_alive"] in q["system"] and M["alive"] not in q["system"])
        a = await turn(http, db, *H, EPH, None, "the hall and the field")
        check("anonymous visitor gets public records only",
              M["public"] in a["system"] and not any(M[k] in a["system"] for k in ("scroll_only", "shared", "signed_in")))
        check("anonymous visitor gets no notes or memories", "Continuity notes" not in a["system"] and "Memories" not in a["system"])
        check("no signed-in fact for anonymous visitor", "signed in" not in a["system"])

        long_hist = [{"role": r, "content": f"turn {i} about the hall"} for i in range(200) for r in ("user", "assistant")]
        lq = await turn(http, db, *H, GUEST, "Test Guest", "the hall and the field", long_hist)
        seen = lq["system"] + lq["user"] + str(lq["history"])
        check("200-turn conversation: no guardian records", not any(M[k] in seen for k in ("scroll_only", "shared", "dog_only")))
        g2 = await turn(http, db, *H, G, "David", "the hall and the field", long_hist)
        check("200-turn conversation: each history capped", g2["system"].count("[2025-04-13") <= 2 * ph.HISTORY_K)

        check("former pod rendered in past tense (no 'I'm' / 'I am')",
              "I'm" not in scrolldog.POD_HISTORY and "I am " not in scrolldog.POD_HISTORY)
        r = await http.post("/api/presence-history/scrolldog-minimal-frame", json={"on": False})
        check("no on/off switch exists", r.status_code in (404, 405), str(r.status_code))

        CAPTURE.clear()
        await http.post("/api/scrolldog/start", json={}, headers=visitor_headers(G))
        check("opening nudge is a plain fact", CAPTURE and CAPTURE[-1]["user"] == "[David has entered.]",
              CAPTURE[-1]["user"] if CAPTURE else "none")
        check("opening prompt has no inherited text", CAPTURE and not [p for p in REMOVED if p in CAPTURE[-1]["system"]])
        orig_user = auth._user_from_request

        # History routes refuse non-guardians
        for who, user in [("anonymous", None), ("guest", {"user_id": GUEST, "role": "guest"}),
                          ("member", {"user_id": "m", "role": "user"})]:
            async def u(_r, _u=user):
                return _u
            auth._user_from_request = u
            codes = [(await http.post("/api/presence-history/import", json={})).status_code,
                     (await http.get("/api/presence-history/summary")).status_code,
                     (await http.post("/api/presence-history/import-session", json={"session_id": "x"})).status_code,
                     (await http.post("/api/presence-history/import-initial-history/daniel")).status_code]
            check(f"history routes refuse {who}", all(c in (401, 403) for c in codes), str(codes))
        auth._user_from_request = orig_user

        # Real route authorization with synthetic callers, separate from the stored owner.
        session_ids = {}
        for owner in (G, GUEST, EPH):
            sid = str(uuid.uuid4())
            session_ids[owner] = sid
            await db.scrolldog_sessions.insert_one({
                "session_id": sid, "user_id": owner, "active": True,
                "messages": [{"role": "user", "content": f"private fixture for {owner}",
                              "timestamp": "9999-01-01"}],
            })

        for owner in (G, GUEST, EPH):
            sid = session_ids[owner]
            base = f"/api/scrolldog/session/{sid}"
            for caller in (G, GUEST, EPH):
                if caller == owner:
                    continue
                headers = visitor_headers(caller)
                CAPTURE.clear()
                read = await http.get(base, headers=headers)
                reply = await http.post("/api/scrolldog/message/stream", headers=headers,
                                        json={"session_id": sid, "content": "hello", "user_id": owner})
                end = await http.post(f"{base}/end", headers=headers)
                check("cross-owner read, reply, and end denied",
                      [read.status_code, reply.status_code, end.status_code] == [404, 404, 404]
                      and not CAPTURE)

            owner_read = await http.get(base, headers=visitor_headers(owner))
            check("owner can read an unchanged session",
                  owner_read.status_code == 200 and owner_read.json().get("active") is True
                  and len(owner_read.json().get("messages", [])) == 1)

        listed = await http.get("/api/presence-history/sessions", headers=visitor_headers(G))
        choices = {item["session_id"] for item in listed.json()}
        check("session import listing excludes guest and ephemeral sessions",
              session_ids[G] in choices and not {session_ids[GUEST], session_ids[EPH]} & choices)
        for owner in (GUEST, EPH):
            copied = await http.post("/api/presence-history/import-session", headers=visitor_headers(G),
                                     json={"session_id": session_ids[owner]})
            check("guardian cannot import another person's or an ephemeral session", copied.status_code == 404)
        copied = await http.post("/api/presence-history/import-session", headers=visitor_headers(G),
                                 json={"session_id": session_ids[G]})
        check("guardian can import their own durable session",
              copied.status_code == 200 and copied.json()["imported"] > 0)
        own_record = await db.presence_history.find_one({"source": f"scrolldog_sessions:{session_ids[G]}"})
        check("session copy keeps owner and guardian visibility",
              own_record and own_record["owner_id"] == G and own_record["visibility"] == "guardian")
        await ph.import_text(db, "Legacy private session copy", {
            "kind": "record", "visibility": "guardian", "positions": ["scrolldog"],
            "source": "scrolldog_sessions:legacy-ownerless",
        })
        records = await ph.retrieve_history(db, "scrolldog", G, "", k=100)
        check("legacy session copy without ownership is excluded",
              not any(row["source"] == "scrolldog_sessions:legacy-ownerless" for row in records))

        # Voice formatting in code
        cleaned = ph.speech_clean("# Heading\n- **bold** item\n1. [link](http://x) `code`")
        check("voice sanitiser strips markdown", not any(c in cleaned for c in "#*[]`") and "http" not in cleaned, repr(cleaned))
    finally:
        auth._user_from_request = original_request_user
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB != os.environ.get("DB_NAME")
        await client.drop_database(TEST_DB)  # throwaway test database created above, never the app's
        user_aliases._GUARDIAN_IDS.discard(G)
        user_aliases._GUESTS.pop(GUEST, None)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")


asyncio.run(main())
