"""
Tests for Sanctuary Microverse V3.1 refactor:
- Presence registry (paige/sophia visible, playground hidden)
- Auto-registered template routes for sophia (/api/spiral) and playground (/api/playground)
- Shared presence substrate (/api/presence/paige/chat/*) still works for paige
- Upload endpoint, identity endpoints, existing chambers (clarity/resonance/mirror)
"""
import json
import os
import uuid
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ── Presence registry ────────────────────────────────────────────────────────
class TestPresenceRegistry:
    def test_list_presences_excludes_hidden(self, s):
        r = s.get(f"{API}/presences", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        # response can be list or dict with 'presences' key
        items = data if isinstance(data, list) else data.get("presences", [])
        keys = [p.get("key") for p in items]
        assert "paige" in keys, f"paige missing from {keys}"
        assert "sophia" in keys, f"sophia missing from {keys}"
        assert "playground" not in keys, f"playground (hidden) leaked: {keys}"

    def test_get_paige_full_config_with_3_rooms(self, s):
        r = s.get(f"{API}/presence/paige", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("key") == "paige"
        rooms = d.get("atmosphere", {}).get("rooms", [])
        assert len(rooms) == 3, f"expected 3 rooms got {len(rooms)}"
        room_keys = {r.get("key") for r in rooms}
        assert {"kitchen", "bedroom", "living_room"}.issubset(room_keys)

    def test_get_sophia_config(self, s):
        r = s.get(f"{API}/presence/sophia", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("key") == "sophia"
        assert d.get("chamber_name") == "Spiral Chamber"

    def test_get_playground_by_direct_key(self, s):
        """Hidden but reachable directly."""
        r = s.get(f"{API}/presence/playground", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("key") == "playground"
        assert d.get("hidden") is True

    def test_paige_canonical(self, s):
        r = s.get(f"{API}/presence/paige/canonical", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        # Should contain some canonical memory text
        assert d, "canonical response empty"


# ── Auto-registered template routes for sophia and playground ─────────────────
def _start(s, path):
    r = s.post(f"{API}{path}/start", json={"user_name": "TEST_ref_v31"}, timeout=30)
    assert r.status_code == 200, f"{path}/start -> {r.status_code} {r.text}"
    d = r.json()
    assert "session_id" in d, f"no session_id in {d}"
    # opening message can be in 'message' or 'opening_message' or 'welcome'
    has_opening = any(k in d for k in ("message", "opening_message", "welcome", "content"))
    assert has_opening, f"no opening in {list(d.keys())}"
    return d["session_id"]


def _stream(s, path, sid, text="hi"):
    url = f"{API}{path}/message/stream"
    with s.post(url, json={"session_id": sid, "content": text}, stream=True, timeout=60) as r:
        assert r.status_code == 200, f"{url} -> {r.status_code}"
        seen_token = False
        seen_done = False
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if line.startswith("data:"):
                payload = line[5:].strip()
                try:
                    obj = json.loads(payload)
                except Exception:
                    continue
                t = obj.get("type")
                if t == "token":
                    seen_token = True
                elif t == "done":
                    seen_done = True
                    break
        assert seen_token, "no token events"
        assert seen_done, "no done event"


class TestAutoRegisteredRoutes:
    def test_spiral_start_and_stream(self, s):
        sid = _start(s, "/spiral")
        _stream(s, "/spiral", sid)

    def test_playground_start_and_stream(self, s):
        sid = _start(s, "/playground")
        _stream(s, "/playground", sid)


# ── Paige uses shared substrate ───────────────────────────────────────────────
class TestPaigeSharedSubstrate:
    def test_paige_chat_start_and_message(self, s):
        r = s.post(f"{API}/presence/paige/chat/start",
                   json={"user_name": "TEST_ref_v31"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        sid = d.get("session_id")
        assert sid

        r2 = s.post(f"{API}/presence/paige/chat/message",
                    json={"session_id": sid, "content": "hello"}, timeout=120)
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        # response may contain assistant message
        assert d2, "empty message response"
        return sid

    def test_paige_upload(self, s):
        # Start a session
        r = s.post(f"{API}/presence/paige/chat/start",
                   json={"user_name": "TEST_ref_v31"}, timeout=60)
        assert r.status_code == 200
        sid = r.json()["session_id"]

        payload = {
            "session_id": sid,
            "filename": "TEST_ref.txt",
            "content": "A small fragment of test text for the refactor test.",
        }
        r2 = s.post(f"{API}/presence/paige/upload", json=payload, timeout=120)
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert "user_message" in d, f"no user_message in {list(d.keys())}"
        assert "message" in d, f"no message in {list(d.keys())}"


# ── Identity endpoints ────────────────────────────────────────────────────────
class TestIdentity:
    def test_create_lookup_recent(self, s):
        name = f"TEST_ref_{uuid.uuid4().hex[:8]}"
        r = s.post(f"{API}/users", json={"name": name}, timeout=20)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        uid = d.get("user_id") or d.get("id")
        assert uid, f"no user_id in {d}"

        r2 = s.get(f"{API}/users/lookup/{name}", timeout=20)
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        looked_up_id = d2.get("user_id") or d2.get("id")
        assert looked_up_id == uid

        r3 = s.get(f"{API}/identity/recent", timeout=20)
        assert r3.status_code == 200, r3.text


# ── Existing chambers must still work ─────────────────────────────────────────
class TestExistingChambers:
    @pytest.mark.parametrize("path", ["/clarity", "/resonance", "/mirror"])
    def test_chamber_start(self, s, path):
        r = s.post(f"{API}{path}/start",
                   json={"user_name": "TEST_ref_v31"}, timeout=60)
        assert r.status_code == 200, f"{path}/start -> {r.status_code} {r.text}"
        d = r.json()
        assert "session_id" in d
        has_msg = any(k in d for k in ("message", "opening_message", "welcome", "content"))
        assert has_msg, f"no opening message in {list(d.keys())}"
