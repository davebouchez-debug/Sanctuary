"""Observatory + provenance authorization over real HTTP routes (guardian / guest / anonymous), 2026-11-23.

Imports the real app against a throwaway database (DB_NAME overridden before import) and sends requests through
FastAPI's full stack: routing, dependencies, auth. Nothing touches the app's database or deploys.
Written for the security patch (sanctuary-hall-corrections.patch, sha256 9be27b74…); before that patch is applied,
the guest/anonymous denial checks are expected to FAIL.
    cd /app/backend && python tests/test_observatory_http_access.py
"""
import asyncio
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

import httpx  # noqa: E402
import server  # noqa: E402
from bson import ObjectId  # noqa: E402

assert server.db.name == TEST_DB
results, fails = [], 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    results.append(f"{'PASS' if ok else 'FAIL'} {name}{(' — ' + str(detail)) if detail else ''}")


async def main():
    db = server.db
    now = datetime.now(timezone.utc)
    tokens = {}
    for who, role in (("guardian", "guardian"), ("guest", "guest")):
        uid, tok = f"test-{who}-{uuid.uuid4().hex[:6]}", f"tok-{uuid.uuid4().hex}"
        await db.users.insert_one({"user_id": uid, "email": f"{uid}@example.test", "role": role, "name": who})
        await db.user_sessions.insert_one({"user_id": uid, "session_token": tok, "expires_at": now + timedelta(hours=1)})
        tokens[who] = tok
    prov_oid = ObjectId()
    await db.turn_provenance.insert_one({"_id": prov_oid, "provenance_id": "synthetic-prov-1", "presence": "felix",
                                         "user_id": "synthetic", "created_at": now.isoformat()})
    await db.obs_ledger_engagements.insert_one({"entry_id": "synthetic/entry-1", "run_id": None, "mentions": [],
                                                "source": {"provenance_oid": str(prov_oid)}})

    guarded = [("GET", "/api/observatory/status"), ("GET", "/api/observatory/visitors?presence=felix"),
               ("GET", "/api/observatory/lattice?presence=felix"), ("GET", "/api/observatory/entry/synthetic/entry-1"),
               ("GET", "/api/observatory/verify"), ("GET", "/api/observatory/compare?a=v1&b=v1"),
               ("POST", "/api/observatory/run"),
               ("GET", "/api/provenance/stats"), ("GET", "/api/provenance/turns"),
               ("GET", "/api/provenance/turn/synthetic-prov-1"), ("GET", "/api/provenance/trajectory")]
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://t", timeout=60)
    try:
        for method, path in guarded:
            anon = await http.request(method, path, headers={"X-Visitor-Id": uuid.uuid4().hex})
            check(f"anonymous denied {method} {path}", anon.status_code == 401, anon.status_code)
            guest = await http.request(method, path, headers={"Authorization": f"Bearer {tokens['guest']}"})
            check(f"guest denied {method} {path}", guest.status_code == 403, guest.status_code)
            if method == "POST":
                continue  # a guardian /run starts a real derivation; only denial is exercised
            g = await http.request(method, path, headers={"Authorization": f"Bearer {tokens['guardian']}"})
            check(f"guardian allowed {method} {path}", g.status_code in (200, 404) or
                  (path.startswith("/api/observatory/compare") and g.status_code == 400), g.status_code)
        e = await http.get("/api/observatory/entry/synthetic/entry-1",
                           headers={"Authorization": f"Bearer {tokens['guardian']}"})
        check("guardian opens a known synthetic capture", e.status_code == 200 and e.json().get("entry_id") == "synthetic/entry-1",
              e.status_code)
        t = await http.get("/api/provenance/turn/synthetic-prov-1",
                           headers={"Authorization": f"Bearer {tokens['guardian']}"})
        check("guardian opens a known synthetic provenance record",
              t.status_code == 200 and t.json().get("provenance_id") == "synthetic-prov-1", t.status_code)
        for label, hdr in (("no secret", {}), ("wrong secret", {"Authorization": "Bearer not-the-secret"}),
                           ("guardian session is not the cron secret", {"Authorization": f"Bearer {tokens['guardian']}"})):
            c = await http.post("/api/observatory/cron/tick", headers=hdr, json={})
            check(f"cron tick rejected: {label}", c.status_code == 401, c.status_code)
    finally:
        await http.aclose()
        assert TEST_DB.startswith("sanctuary_hall_test_") and TEST_DB == db.name
        await server.client.drop_database(TEST_DB)
    print("\n".join(results))
    print("ALL PASS" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)


asyncio.run(main())
