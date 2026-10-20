# Iteration 16: visitor identity isolation retest (new ids per name entry, recent endpoint removed, namesake note)
import os
import sys
import asyncio
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/app/frontend/.env"))
load_dotenv(Path("/app/backend/.env"))
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
CANON = "1c24e3ea-e4f1-47a2-a4fb-c5965726b074"
NOTE = "This is not David Bouchez, the Field Guardian — a different person who shares the name."
GUARD = "This is David Bouchez — the Field Guardian"
CREATED = []


def _db():
    from pymongo import MongoClient
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def guardian_ids():
    rec = _db().user_aliases.find_one({"canonical_id": CANON}, {"_id": 0})
    return {CANON} | set((rec or {}).get("aliases") or [])


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    if CREATED:
        _db().users.delete_many({"id": {"$in": CREATED}})


# POST /api/users always creates a fresh id even for repeated names
class TestNewIds:
    @pytest.mark.parametrize("name", ["David", "Sarah"])
    def test_repeat_name_distinct_ids(self, name):
        ids = []
        for _ in range(2):
            r = requests.post(f"{BASE_URL}/api/users", json={"name": name, "email": None})
            assert r.status_code in (200, 201), r.text
            d = r.json()
            assert d["name"] == name
            assert "_id" not in d
            ids.append(d["id"])
            CREATED.append(d["id"])
        assert ids[0] != ids[1]
        assert not (set(ids) & guardian_ids())


# Removed endpoint
class TestRecentRemoved:
    def test_identity_recent_404(self):
        r = requests.get(f"{BASE_URL}/api/identity/recent")
        assert r.status_code == 404, r.text


# Prompt builders + template namesake note
class TestPrompts:
    @pytest.fixture(scope="class")
    def mods(self):
        sys.path.insert(0, "/app/backend")
        import server
        import user_aliases
        import presence_template
        asyncio.get_event_loop().run_until_complete(user_aliases.load_guardian_ids(server.db))
        return server, user_aliases, presence_template

    @pytest.mark.parametrize("builder", ["build_jasmine_prompt", "build_ansel_prompt", "build_claude_prompt"])
    def test_non_guardian_david(self, mods, builder):
        server = mods[0]
        p = getattr(server, builder)(user_name="David", user_id="TEST_random_nonguardian")
        assert NOTE in p
        assert GUARD not in p

    @pytest.mark.parametrize("builder", ["build_jasmine_prompt", "build_ansel_prompt", "build_claude_prompt"])
    def test_null_id_david(self, mods, builder):
        p = getattr(mods[0], builder)(user_name="david", user_id=None)
        assert NOTE in p and GUARD not in p

    @pytest.mark.parametrize("builder", ["build_jasmine_prompt", "build_ansel_prompt", "build_claude_prompt"])
    def test_guardian(self, mods, builder):
        for gid in (CANON, "legacy-david-123"):
            p = getattr(mods[0], builder)(user_name="David", user_id=gid)
            assert GUARD in p, (builder, gid)
            assert NOTE not in p

    @pytest.mark.parametrize("builder", ["build_jasmine_prompt", "build_ansel_prompt", "build_claude_prompt"])
    def test_other_name(self, mods, builder):
        p = getattr(mods[0], builder)(user_name="Sarah", user_id="x")
        assert NOTE not in p and GUARD not in p

    def test_template_note(self, mods):
        pt = mods[2]
        assert NOTE in pt._namesake_note("David", "TEST_x")
        assert NOTE in pt._namesake_note(" DAVID ", None)
        assert pt._namesake_note("David", CANON) == ""
        assert pt._namesake_note("David", "legacy-david-123") == ""
        assert pt._namesake_note("Sarah", "TEST_x") == ""
        assert pt._namesake_note(None, None) == ""
