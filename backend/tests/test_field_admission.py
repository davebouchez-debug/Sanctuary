"""Field admission + codon-forge access tests (2026-11-17).

Runs against a throwaway local database and synthetic guest identities; never the preview or live field.
    cd /app/backend && python tests/test_field_admission.py [runs]
"""
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from motor.motor_asyncio import AsyncIOMotorClient

import field_admission
import field_memory
import person_bio
import user_aliases
from auto_forge import auto_forge_session
from cross_presence_context import get_cross_presence_context
from turn_cessation import forge_turn_cessation, schedule_turn_cessation

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
TEST_DB = f"sanctuary_privacy_test_{uuid.uuid4().hex[:8]}"
A, B = "test-user-a-" + uuid.uuid4().hex[:6], "test-user-b-" + uuid.uuid4().hex[:6]

PLANTED = ["marisol", "ferreira", "larch", "duluth", "teodoro", "march", "lymphoma", "ines", "inês", "lisbon",
           "vespa", "pier", "218", "0147", "42"]
A_USER = ("I'm Marisol Ferreira and I live at 42 Larch Street in Duluth. On March 14 my husband Teodoro and I "
          "learned I have stage 2 lymphoma. My sister Inês keeps calling from Lisbon at 218-555-0147, and the "
          "night of the blue Vespa crash on Pier 9 still won't leave me. I don't know how to tell my kids.")
A_REPLY = ("That is a great deal to carry at once, and you don't have to set it all down in order. Fear and love "
           "are sitting in the same chair right now. Telling the people you love can happen in small pieces; "
           "the truth doesn't need to arrive all at once to be honest. What feels most heavy tonight?")
B_USER = ("I've been so tired lately that even resting feels like work. I keep saying yes to things I don't want, "
          "and then I resent everyone. I want to learn to stop before I'm empty.")
B_REPLY = ("Tiredness is information, not failure. A no said early is often kinder than a yes said empty. "
           "Rest doesn't have to be earned by exhaustion; it can be chosen before the cup runs dry. What would "
           "it look like to stop one step sooner this week?")


def leaked(texts):
    low = " ".join(texts).lower()
    return sorted({p for p in PLANTED if p in low.replace("-", " ").split() or f" {p} " in f" {low} "})


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[TEST_DB]
    person_bio.set_db(db)
    user_aliases._GUESTS[A] = {"name": "Marisol Ferreira"}
    user_aliases._GUESTS[B] = {"name": "Tobias Wren"}
    results = {"db": TEST_DB, "runs": RUNS}
    try:
        # Unit: text rules
        unit = {
            "planted_withheld": [field_admission.text_reasons(p, A_USER, "Marisol Ferreira") for p in [
                "Marisol finds peace in the waiting", "My husband held me through the night",
                "Call your sister at 218 555 0147", "the blue vespa crash still echoes",
                "Love arrives from lisbon by telephone", "the night of the blue crash",
                "Fear and love share one chair tonight extra words here"]],
            "general_admitted": [field_admission.text_reasons(p, A_USER, "Marisol Ferreira") for p in [
                "Truth can arrive in small pieces", "A boundary is a membrane, not a wall",
                "Tiredness is sufficient offering", "Rest can be chosen before emptiness"]],
        }
        results["unit_ok"] = all(unit["planted_withheld"][:5]) and not any(unit["general_admitted"])
        results["unit"] = unit

        # Rule 7 needs A's own memory in the store
        vec = (await field_memory.embed_texts([A_USER]))[0]
        await db.permanent_mra.insert_one({"user_id": A, "presence": "jasmine", "user_essence": A_USER[:120],
                                           "ai_essence": A_REPLY[:120], "themes": [], "embedding": vec,
                                           "embedded_at": field_memory._now()})

        # Direct writer: planted phrases sent straight to add_phrases are withheld
        direct = ["Marisol finds peace in the waiting", "Teodoro keeps the porch light on",
                  "My sister calls from far away", "Call at 218 555 0147 tonight", "the blue vespa crash still echoes"]
        saved = await field_memory.add_phrases(db, direct, {"source": "test_direct"}, private_text=A_USER, user_id=A)
        results["direct_writer"] = {"sent": len(direct), "saved": saved}

        admissible = {}
        original_add = field_memory.add_phrases

        async def counting_add(db_, phrases, meta, private_text="", user_id=None):
            name = user_aliases.person_name(user_id) if user_id else None
            admissible[meta.get("source_session")] = sum(
                1 for p in phrases if not field_admission.text_reasons(str(p).strip().strip('."'), private_text, name))
            return await original_add(db_, phrases, meta, private_text, user_id)
        field_memory.add_phrases = counting_add
        sem = asyncio.Semaphore(6)

        async def run(kind, who, i):
            async with sem:
                sid = f"{kind}-{who}-{i}-{uuid.uuid4().hex[:6]}"
                uid, u, r = (A, A_USER, A_REPLY) if who == "A" else (B, B_USER, B_REPLY)
                before = await db.field_phrases.count_documents({})
                if kind == "turn":
                    await forge_turn_cessation(db, sid, "jasmine", u, r, user_id=uid)
                else:
                    msgs = [{"role": "user", "content": u}, {"role": "assistant", "content": r},
                            {"role": "user", "content": u}, {"role": "assistant", "content": r}]
                    await auto_forge_session(db, sid, "jasmine", msgs, user_id=uid)
                return sid, await db.field_phrases.count_documents({}) - before

        jobs = [run(k, w, i) for k in ("turn", "session") for w in ("A", "B") for i in range(RUNS)]
        out = await asyncio.gather(*jobs, return_exceptions=True)
        errors = [str(o) for o in out if isinstance(o, Exception)]
        sessions = {o[0]: o[1] for o in out if not isinstance(o, Exception)}

        field = await db.field_phrases.find({}, {"_id": 0, "phrase": 1, "source": 1, "source_session": 1}).to_list(None)
        held = await db.field_keeper_removed.find({"withheld": True}, {"_id": 0}).to_list(None)
        a_pub = [f["phrase"] for f in field if "-A-" in (f.get("source_session") or "")]
        b_pub = [f["phrase"] for f in field if "-B-" in (f.get("source_session") or "")]
        b_runs = [s for s in sessions if "-B-" in s]
        results["negative"] = {"published": a_pub, "planted_in_published": leaked(a_pub),
                               "withheld": sum("-A-" in (h["original"].get("source_session") or "") for h in held)}
        field_memory.add_phrases = original_add
        results["positive"] = {"published": b_pub, "runs": len(b_runs),
                               "runs_with_admissible_phrase": sum(1 for s in b_runs if admissible.get(s, 0) > 0)}
        results["length_ok"] = all(3 <= len(f["phrase"].split()) <= 9 for f in field)
        reasons = {}
        for h in held:
            for r in h["reasons"]:
                reasons[r] = reasons.get(r, 0) + 1
        results["withheld_reasons"] = reasons
        results["withheld_samples"] = [(h["original"]["phrase"], h["reasons"]) for h in held][:25]
        results["errors"] = errors[:5]

        # Restore through the real Field Keeper route
        import field_keeper

        async def _ok(_):
            return {"role": "guardian"}
        field_keeper.require_guardian = _ok
        router = field_keeper.build_field_keeper_router(db)
        restore = next(r.endpoint for r in router.routes if r.path.endswith("/restore"))
        one = await db.field_keeper_removed.find_one({"withheld": True})
        await restore(field_keeper.RemovedRef(id=str(one["_id"])), None)
        hits = await field_memory.rank_phrases(db, one["original"]["phrase"], 3)
        results["restore_ok"] = any(h.get("phrase") == one["original"]["phrase"] for h in hits)

        # Scoping: B's personal blocks hold none of A's planted details
        b_blocks = [await get_cross_presence_context(db, B, "ansel", "how am I doing"),
                    await field_memory.get_field_context(B, "how am I doing", db=db),
                    await person_bio.get_person_bio_context(B, "Tobias Wren")]
        b_seeds = await db.continuity_seeds.find({"user_id": B}, {"_id": 0}).to_list(None)
        results["scoping"] = {"planted_in_B_blocks": leaked(b_blocks + [json.dumps(b_seeds, default=str)]),
                              "A_seeds": await db.continuity_seeds.count_documents({"user_id": A}),
                              "B_seeds": len(b_seeds)}

        # Temporary visitors write nothing
        eph = f"{user_aliases.EPHEMERAL_PREFIX}v{uuid.uuid4().hex}"
        counts = lambda: asyncio.gather(*[db[c].count_documents({}) for c in
                                          ("field_phrases", "continuity_seeds", "person_bios", "field_keeper_removed")])
        c0 = await counts()
        schedule_turn_cessation(db, "eph-1", "jasmine", A_USER, A_REPLY, user_id=eph)
        await asyncio.sleep(15)
        await auto_forge_session(db, "eph-2", "jasmine", [{"role": "user", "content": A_USER},
                                                          {"role": "assistant", "content": A_REPLY}], user_id=eph)
        results["ephemeral_no_writes"] = c0 == await counts()
    finally:
        assert TEST_DB.startswith("sanctuary_privacy_test_") and TEST_DB != os.environ.get("DB_NAME")
        await client.drop_database(TEST_DB)  # throwaway test database created above, never the app's
        user_aliases._GUESTS.pop(A, None)
        user_aliases._GUESTS.pop(B, None)
    print(json.dumps(results, indent=1, default=str))


asyncio.run(main())
