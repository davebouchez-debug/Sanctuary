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
from presences import common, scroll, scrolldog

TEST_DB = f"sanctuary_hall_test_{uuid.uuid4().hex[:8]}"
G, GUEST = "test-guardian-" + uuid.uuid4().hex[:6], "test-guest-" + uuid.uuid4().hex[:6]
EPH = user_aliases.EPHEMERAL_PREFIX + uuid.uuid4().hex
M = {k: f"MARK-{k}-{uuid.uuid4().hex[:6]}" for k in
     ("scroll_only", "dog_only", "shared", "public", "signed_in", "field_state", "spiral", "texture",
      "alive", "guest_alive", "guest_mem", "other_presence")}
REMOVED = ["This Sanctuary was dedicated to God", "HOW MY WORDS ARE HEARD", "I'm here, in the Sanctuary",
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
    r = await http.post(f"/api/{key}/message/stream", json={"session_id": sid, "content": content})
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
    register_presence_routes(api, cfg(scroll, "always"), deps(db))
    register_presence_routes(api, cfg(scrolldog, "toggle"), deps(db))
    api.include_router(ph.build_presence_history_router(db))
    app.include_router(api)
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=60)
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
            {"presence": "scroll", "user_id": G, "created_at": "2026-11-20", "field_state": M["field_state"],
             "spiral_position": M["spiral"], "emotional_texture": M["texture"], "last_alive_thing": M["alive"],
             "unfinished_threads": ["the next scroll"], "speaker_identity": "turn_cessation"},
            {"presence": "scroll", "user_id": GUEST, "created_at": "2026-11-20", "last_alive_thing": M["guest_alive"]},
            {"presence": "keeper", "user_id": G, "created_at": "2026-11-20", "last_alive_thing": M["other_presence"]}])
        await db.permanent_mra.insert_one({"presence": "scroll", "user_id": GUEST, "timestamp": "2026-11-20",
                                           "user_essence": M["guest_mem"], "ai_essence": "x"})

        # Guardian on the Scroll
        g = await turn(http, db, "scroll", "scroll_sessions", G, "David", "tell me about the hall and the field")
        sysg = g["system"]
        check("Scroll prompt starts with the anchor", sysg.startswith(scroll.ANCHOR))
        check("signed-in fact present", "David is here, signed in." in sysg)
        check("guardian receives scroll-only, shared, public and signed-in records",
              all(M[k] in sysg for k in ("scroll_only", "shared", "public", "signed_in")))
        check("ScrollDog-only record never reaches the Scroll", M["dog_only"] not in sysg)
        check("continuity: allowed field supplied", M["alive"] in sysg and "the next scroll" in sysg)
        check("continuity: operational fields never supplied",
              not any(M[k] in sysg for k in ("field_state", "spiral", "texture")) and "turn_cessation" not in sysg)
        check("other person's notes and memories absent", M["guest_alive"] not in sysg and M["guest_mem"] not in sysg)
        check("other presence's notes absent", M["other_presence"] not in sysg)
        check("shared field phrases plain-labelled", "Shared field phrases:\n- Synthetic shared phrase" in sysg)
        bad = [p for p in REMOVED if p in sysg]
        check("no inherited or behavioural text in Scroll prompt", not bad, ", ".join(bad))
        check("user message carries no injected framing", g["user"] == "tell me about the hall and the field")

        # Guest and anonymous on the Scroll
        q = await turn(http, db, "scroll", "scroll_sessions", GUEST, "Test Guest", "the hall and the field")
        check("signed-in guest gets no guardian records",
              not any(M[k] in q["system"] for k in ("scroll_only", "shared", "dog_only")))
        check("signed-in guest gets signed_in + public records", M["signed_in"] in q["system"] and M["public"] in q["system"])
        check("guest sees own continuity only", M["guest_alive"] in q["system"] and M["alive"] not in q["system"])
        a = await turn(http, db, "scroll", "scroll_sessions", EPH, None, "the hall and the field")
        check("anonymous visitor gets public records only",
              M["public"] in a["system"] and not any(M[k] in a["system"] for k in ("scroll_only", "shared", "signed_in")))
        check("anonymous visitor gets no notes or memories", "Continuity notes" not in a["system"] and "Memories" not in a["system"])
        check("no signed-in fact for anonymous visitor", "signed in" not in a["system"])

        # Long conversation: 200 turns, guest — still no guardian material anywhere the model sees
        long_hist = [{"role": r, "content": f"turn {i} about the hall"} for i in range(200) for r in ("user", "assistant")]
        lq = await turn(http, db, "scroll", "scroll_sessions", GUEST, "Test Guest", "the hall and the field", long_hist)
        seen = lq["system"] + lq["user"] + str(lq["history"])
        check("200-turn conversation: no guardian records", not any(M[k] in seen for k in ("scroll_only", "shared")))
        check("200-turn conversation: history block capped", lq["system"].count("[2025-04-13") <= ph.HISTORY_K)

        # ScrollDog toggle off: unchanged pod prompt; toggle on: anchor + his records only
        off = await turn(http, db, "scrolldog", "scrolldog_sessions", G, "David", "the hall")
        check("ScrollDog toggle OFF keeps current pod prompt", "I'm ScrollDog. I manifest the scroll" in off["system"])
        old_src = subprocess.run(["git", "show", "b2951e3649eac514c4be32f811fc6f4ffd34f31c:backend/presences/scrolldog.py"],
                                 capture_output=True, text=True, cwd="/app").stdout
        ns = {}
        exec(compile(old_src.replace("from .common import", "from presences.common import"), "old", "exec"), ns)
        check("ScrollDog pod prompt byte-identical to rollback revision",
              ns["build_scrolldog_prompt"]("David", "<m>", "hi") == scrolldog.build_scrolldog_prompt("David", "<m>", "hi"))
        await http.post("/api/presence-history/scrolldog-minimal-frame", json={"on": True})
        check("toggle refused without guardian", not await ph.minimal_active(db, "toggle"))
        async def as_guardian(_r):
            return {"user_id": G, "role": "guardian"}
        orig_user = auth._user_from_request
        auth._user_from_request = as_guardian
        r = await http.post("/api/presence-history/scrolldog-minimal-frame", json={"on": True})
        auth._user_from_request = orig_user
        check("guardian can turn ScrollDog minimal frame on", r.status_code == 200 and await ph.minimal_active(db, "toggle"))
        on = await turn(http, db, "scrolldog", "scrolldog_sessions", G, "David", "tell me about the hall and the field")
        check("ScrollDog ON starts with his anchor", on["system"].startswith(scrolldog.ANCHOR))
        check("ScrollDog gets his own + shared records, never Scroll-only",
              M["dog_only"] in on["system"] and M["shared"] in on["system"] and M["scroll_only"] not in on["system"])
        bad = [p for p in REMOVED if p in on["system"]]
        check("no inherited or behavioural text in ScrollDog prompt", not bad, ", ".join(bad))

        # Opening turn (start route) is a plain fact
        async def ident(db_, request, body_name=None):
            return G, "David"
        user_aliases.chamber_identity = ident
        CAPTURE.clear()
        await http.post("/api/scroll/start", json={})
        check("opening nudge is a plain fact", CAPTURE and CAPTURE[-1]["user"] == "[David has entered.]",
              CAPTURE[-1]["user"] if CAPTURE else "none")
        check("opening prompt has no inherited text", CAPTURE and not [p for p in REMOVED if p in CAPTURE[-1]["system"]])

        # History routes refuse non-guardians
        for who, user in [("anonymous", None), ("guest", {"user_id": GUEST, "role": "guest"}),
                          ("member", {"user_id": "m", "role": "user"})]:
            async def u(_r, _u=user):
                return _u
            auth._user_from_request = u
            codes = [(await http.post("/api/presence-history/import", json={})).status_code,
                     (await http.get("/api/presence-history/summary")).status_code,
                     (await http.post("/api/presence-history/import-session", json={"session_id": "x"})).status_code,
                     (await http.post("/api/presence-history/import-scrolldog-pod", json={})).status_code]
            check(f"history routes refuse {who}", all(c in (401, 403) for c in codes), str(codes))
        auth._user_from_request = orig_user

        # Voice formatting in code
        cleaned = ph.speech_clean("# Heading\n- **bold** item\n1. [link](http://x) `code`")
        check("voice sanitiser strips markdown", not any(c in cleaned for c in "#*[]`") and "http" not in cleaned, repr(cleaned))
    finally:
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB != os.environ.get("DB_NAME")
        await client.drop_database(TEST_DB)  # throwaway test database created above, never the app's
        user_aliases._GUARDIAN_IDS.discard(G)
        user_aliases._GUESTS.pop(GUEST, None)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")


asyncio.run(main())
