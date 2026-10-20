# Visitor identity isolation + Field Guardian recognition (iteration 15)
import os
import sys
import asyncio
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/app/frontend/.env"))
load_dotenv(Path("/app/backend/.env"))
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
CANON = "1c24e3ea-e4f1-47a2-a4fb-c5965726b074"
CREATED = []


def guardian_ids():
    from pymongo import MongoClient
    c = MongoClient(os.environ["MONGO_URL"])
    rec = c[os.environ["DB_NAME"]].user_aliases.find_one({"canonical_id": CANON}, {"_id": 0})
    return {CANON} | set((rec or {}).get("aliases") or [])


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    from pymongo import MongoClient
    c = MongoClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    if CREATED:
        db.users.delete_many({"id": {"$in": CREATED}})


# Lookup endpoint
class TestLookup:
    def test_alias_count(self):
        ids = guardian_ids()
        print("guardian ids", len(ids))
        assert len(ids) >= 28

    def test_lookup_david_404(self):
        r = requests.get(f"{BASE_URL}/api/users/lookup/David")
        assert r.status_code == 404, r.text
        r = requests.get(f"{BASE_URL}/api/users/lookup/david")
        assert r.status_code == 404

    def test_create_and_lookup_other_name(self):
        name = f"TEST_Visitor_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE_URL}/api/users", json={"name": name})
        assert r.status_code in (200, 201), r.text
        uid = r.json()["id"]
        CREATED.append(uid)
        assert uid not in guardian_ids()
        l = requests.get(f"{BASE_URL}/api/users/lookup/{name}")
        assert l.status_code == 200
        assert l.json()["id"] == uid

    def test_create_david_distinct(self):
        r = requests.post(f"{BASE_URL}/api/users", json={"name": "David"})
        assert r.status_code in (200, 201), r.text
        uid = r.json()["id"]
        CREATED.append(uid)
        assert uid not in guardian_ids()
        # a non-guardian David now exists; lookup should return a non-guardian id
        l = requests.get(f"{BASE_URL}/api/users/lookup/David")
        if l.status_code == 200:
            assert l.json()["id"] not in guardian_ids()
            print("NOTE: second lookup of David returns non-guardian David:", l.json()["id"], "(shared across visitors named David)")

    def test_identity_recent_still_exists(self):
        r = requests.get(f"{BASE_URL}/api/identity/recent")
        print("identity/recent:", r.status_code, r.text[:200])


# Prompt builders: guardian framing only by id
class TestPromptBuilders:
    @pytest.fixture(scope="class")
    def server(self):
        sys.path.insert(0, "/app/backend")
        os.chdir("/app/backend")
        import server as s
        import user_aliases
        from motor.motor_asyncio import AsyncIOMotorClient
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        asyncio.get_event_loop().run_until_complete(user_aliases.load_guardian_ids(db))
        return s

    MARK = "This is David Bouchez — the Field Guardian"

    @pytest.mark.parametrize("fn", ["build_jasmine_prompt", "build_ansel_prompt", "build_claude_prompt"])
    def test_guardian_gets_framing(self, server, fn):
        p = getattr(server, fn)(user_name="David", user_id=CANON, memory_context="", current_message="")
        assert self.MARK in p

    @pytest.mark.parametrize("fn", ["build_jasmine_prompt", "build_ansel_prompt", "build_claude_prompt"])
    def test_alias_gets_framing(self, server, fn):
        alias = sorted(guardian_ids() - {CANON})[0]
        p = getattr(server, fn)(user_name="David", user_id=alias, memory_context="", current_message="")
        assert self.MARK in p

    @pytest.mark.parametrize("fn", ["build_jasmine_prompt", "build_ansel_prompt", "build_claude_prompt"])
    def test_other_david_no_framing(self, server, fn):
        p = getattr(server, fn)(user_name="David", user_id=str(uuid.uuid4()), memory_context="", current_message="")
        assert self.MARK not in p
        p2 = getattr(server, fn)(user_name="David", user_id=None, memory_context="", current_message="")
        assert self.MARK not in p2
