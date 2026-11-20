"""Codon export v1 tests — throwaway database, synthetic records only.
    cd /app/backend && python tests/test_codon_export.py
"""
import asyncio
import hashlib
import io
import json
import os
import sys
import uuid
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
import bson
import httpx
import numpy as np
from bson import Binary, ObjectId, json_util
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

import codon_export

TEST_DB = f"sanctuary_export_test_{uuid.uuid4().hex[:8]}"
TOKEN = uuid.uuid4().hex + uuid.uuid4().hex
PLANT = "PRIVATE-PLANT-" + uuid.uuid4().hex[:6]
results, fails = [], 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    results.append(f"{'PASS' if ok else 'FAIL'} {name}{(' — ' + detail) if detail else ''}")


def vec():
    v = np.random.rand(384).astype(np.float32)
    return Binary((v / np.linalg.norm(v)).astype("<f4").tobytes())


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[TEST_DB]
    app = FastAPI()
    app.include_router(codon_export.build_codon_export_router(db), prefix="/api")
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
    url, auth = "/api/codon-export/v1/snapshot", {"Authorization": f"Bearer {TOKEN}"}
    try:
        docs = [
            {"_id": ObjectId(), "phrase": "Tiredness is sufficient offering", "presence": "field", "embedding": vec(),
             "created_at": "2026-11-18T10:00:00+00:00", "embedded_at": "2026-11-18T10:00:00+00:00",
             "source": "turn_cessation", "source_presence": "jasmine", "source_session": PLANT + "-session"},
            {"_id": ObjectId(), "phrase": "A boundary is a membrane, not a wall", "presence": "field",
             "embedding": [float(x) for x in np.random.rand(384)], "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
             "embedded_at": "2026-11-02T00:00:00+00:00", "source": "legacy_translation",
             "legacy_name": "Membrane", "legacy_presence": "ansel"},
            {"_id": ObjectId(), "phrase": "Rest can be chosen before emptiness", "presence": "field", "embedding": vec(),
             "created_at": "2026-11-18T11:00:00+00:00", "embedded_at": "2026-11-18T11:00:00+00:00",
             "source": "codon_forge", "lens": "relational", "source_file": PLANT + "-file.txt",
             "visitor_email": PLANT + "@example.com", "count": bson.int64.Int64(7)},
        ]
        await db.field_phrases.insert_many(docs)
        await db.permanent_mra.insert_one({"user_id": PLANT, "user_essence": PLANT})
        await db.continuity_seeds.insert_one({"user_id": PLANT, "field_state": PLANT})
        await db.field_keeper_removed.insert_one({"withheld": True, "original": {"phrase": PLANT + " withheld"}})

        # Authorization
        os.environ.pop("CODON_EXPORT_TOKEN", None)
        r = await http.get(url, headers=auth)
        check("token not configured -> 503", r.status_code == 503, str(r.status_code))
        os.environ["CODON_EXPORT_TOKEN"] = TOKEN
        for name, h in [("no header", {}), ("wrong token", {"Authorization": "Bearer " + "x" * 64}),
                        ("token without Bearer", {"Authorization": TOKEN}),
                        ("guardian cookie only", {"Cookie": "session_token=anything"})]:
            r = await http.get(url, headers=h)
            check(f"{name} -> 401", r.status_code == 401 and "zip" not in r.headers.get("content-type", ""),
                  str(r.status_code))
        r = await http.post(url, headers=auth)
        check("POST not allowed -> 405", r.status_code == 405, str(r.status_code))

        # Good request
        before = {c: await db[c].count_documents({}) for c in await db.list_collection_names()}
        r = await http.get(url, headers=auth)
        check("valid token -> 200 zip", r.status_code == 200 and r.headers["content-type"] == "application/zip")
        data = r.content
        check("X-Content-SHA256 matches body", r.headers["x-content-sha256"] == hashlib.sha256(data).hexdigest())
        z = zipfile.ZipFile(io.BytesIO(data))
        check("ZIP has exactly manifest.json + field_phrases.jsonl",
              sorted(z.namelist()) == ["field_phrases.jsonl", "manifest.json"])
        mb, body = z.read("manifest.json"), z.read("field_phrases.jsonl")
        m = json.loads(mb)
        check("X-Manifest-SHA256 matches manifest", r.headers["x-manifest-sha256"] == hashlib.sha256(mb).hexdigest())
        f = m["files"]["field_phrases.jsonl"]
        check("manifest sha256/bytes match file", f["sha256"] == hashlib.sha256(body).hexdigest() and f["bytes"] == len(body))
        lines = body.decode("utf-8").splitlines()
        check("record_count matches lines and DB", m["record_count"] == len(lines) == 3 and m["complete"] is True)
        ids = [json_util.loads(l)["_id"] for l in lines]
        check("sorted by _id, ids_sha256 matches",
              ids == sorted(ids) and m["ids_sha256"] == hashlib.sha256("\n".join(map(str, ids)).encode()).hexdigest())

        # Exact preservation of allowlisted fields (types included)
        back = {d["_id"]: d for d in (json_util.loads(l) for l in lines)}
        exact = all(bson.encode(back[d["_id"]]) == bson.encode({k: d[k] for k in codon_export.FIELDS if k in d})
                    for d in docs)
        check("ids, text, timestamps, embeddings preserved byte-exact (BSON re-encode)", exact)
        check("ObjectId / datetime / binary types kept",
              isinstance(back[docs[0]["_id"]]["_id"], ObjectId)
              and isinstance(back[docs[1]["_id"]]["created_at"], datetime)
              and isinstance(back[docs[0]["_id"]]["embedding"], bytes)
              and len(back[docs[0]["_id"]]["embedding"]) == 1536)

        # Privacy exclusions
        check("no private plant anywhere in ZIP", PLANT.encode() not in body and PLANT.encode() not in mb)
        check("source_session / source_file / unknown fields not exported",
              all(not ({"source_session", "source_file", "visitor_email", "count"} & set(b)) for b in back.values()))
        check("manifest names withheld field names only",
              set(m["fields_not_exported"]) == {"source_session", "source_file", "visitor_email", "count"})

        # No writes
        after = {c: await db[c].count_documents({}) for c in await db.list_collection_names()}
        check("export wrote nothing", before == after)

        # Concurrent change between reads -> retried, final snapshot complete and consistent
        orig = codon_export._read
        calls = {"n": 0}

        async def insert_once(db_):
            calls["n"] += 1
            out = await orig(db_)
            if calls["n"] == 1:
                await db.field_phrases.insert_one({"phrase": "Arrived mid-read", "presence": "field",
                                                   "embedding": vec(), "created_at": "x", "embedded_at": "x"})
            return out
        codon_export._read = insert_once
        r = await http.get(url, headers=auth)
        m2 = json.loads(zipfile.ZipFile(io.BytesIO(r.content)).read("manifest.json"))
        check("insert during read -> retried, new record included",
              r.status_code == 200 and m2["record_count"] == 4 and m2["consistency"]["attempts"] == 2,
              f"{r.status_code} attempts={m2['consistency']['attempts']}")

        async def remove_once(db_):
            calls["n"] += 1
            out = await orig(db_)
            if calls["n"] == 1:
                await db.field_phrases.delete_one({"phrase": "Arrived mid-read"})
            return out
        calls["n"] = 0
        codon_export._read = remove_once
        r = await http.get(url, headers=auth)
        m3 = json.loads(zipfile.ZipFile(io.BytesIO(r.content)).read("manifest.json"))
        check("removal during read -> retried, removed record absent", r.status_code == 200 and m3["record_count"] == 3)

        async def always_changing(db_):
            out = await orig(db_)
            await db.field_phrases.insert_one({"phrase": uuid.uuid4().hex, "presence": "field"})
            return out
        codon_export._read = always_changing
        r = await http.get(url, headers=auth)
        check("never-stable field -> 503, no ZIP",
              r.status_code == 503 and "zip" not in r.headers.get("content-type", ""), str(r.status_code))

        async def broken(db_):
            raise RuntimeError("db down")
        codon_export._read = broken
        r = await http.get(url, headers=auth)
        check("read failure -> 500, no ZIP",
              r.status_code == 500 and "zip" not in r.headers.get("content-type", ""), str(r.status_code))
        codon_export._read = orig
    finally:
        assert TEST_DB.startswith("sanctuary_export_test_") and TEST_DB != os.environ.get("DB_NAME")
        await client.drop_database(TEST_DB)  # throwaway test database created above, never the app's
        os.environ.pop("CODON_EXPORT_TOKEN", None)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")


asyncio.run(main())
