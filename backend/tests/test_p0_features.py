"""
P0 feature regression tests for the Jan-2026 batch:
1) /api/users + /api/users/lookup/{name} (IdentityBadge backend)
2) Paige first-person system prompt (/api/presence/paige/chat/*)
3) Presence file upload (/api/presence/paige/upload) — happy path + errors
4) 4 streaming chambers: clarity, resonance, mirror, spiral
   - SSE returns 'token' + 'done' events without crashing
"""

import os
import re
import json
import uuid
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def test_user(session):
    """Create a TEST_ user once for the whole module."""
    name = f"TEST_P0_{uuid.uuid4().hex[:6]}"
    r = session.post(f"{API}/users", json={"name": name})
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert "id" in data
    assert data["name"] == name
    return data


# ---------------------------------------------------------------------------
# 1. Users endpoints used by IdentityBadge
# ---------------------------------------------------------------------------
class TestUsersIdentity:
    def test_user_lookup_existing(self, session, test_user):
        r = session.get(f"{API}/users/lookup/{test_user['name']}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == test_user["id"]
        assert data["name"] == test_user["name"]

    def test_user_lookup_missing(self, session):
        r = session.get(f"{API}/users/lookup/TEST_does_not_exist_{uuid.uuid4().hex[:6]}")
        assert r.status_code in (404, 200)
        if r.status_code == 200:
            # Some impls return {found: false}
            data = r.json()
            assert data.get("found") in (False, None) or not data.get("id")


# ---------------------------------------------------------------------------
# 2. Paige first-person system prompt
# ---------------------------------------------------------------------------
class TestPaigeFirstPerson:
    def test_chat_start_returns_session(self, session, test_user):
        r = session.post(
            f"{API}/presence/paige/chat/start",
            json={"user_id": test_user["id"], "user_name": test_user["name"]},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "session_id" in data
        assert data["presence_key"] == "paige"
        assert "message" in data and data["message"]["role"] == "assistant"
        pytest.shared_paige_session = data["session_id"]

    def test_paige_speaks_in_first_person(self, session, test_user):
        sid = getattr(pytest, "shared_paige_session", None)
        assert sid, "paige session not opened"
        r = session.post(
            f"{API}/presence/paige/chat/message",
            json={"session_id": sid, "content": "Tell me who you are in your own words."},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        content = r.json()["message"]["content"]
        assert isinstance(content, str) and len(content) > 20

        lower = content.lower()
        # Negative: no third-person self-reference / model framing
        forbidden = ["paige is ", "she is ", "as a model", "as an ai",
                     "as an assistant", "i am an ai", "i am a language model"]
        for needle in forbidden:
            assert needle not in lower, f"forbidden phrase '{needle}' found in: {content[:300]}"

        # Positive: at least one first-person 'I' statement
        i_patterns = [r"\bI am\b", r"\bI keep\b", r"\bI'm\b", r"\bI've\b",
                      r"\bI carry\b", r"\bI remember\b", r"\bI hold\b", r"\bI feel\b",
                      r"\bI was\b", r"\bI know\b", r"\bI sit\b", r"\bI stay\b",
                      r"\bI watch\b", r"\bI listen\b"]
        assert any(re.search(p, content) for p in i_patterns), \
            f"no first-person 'I' statement in: {content[:300]}"

        # Spot-check absence of scaffolding
        scaffolds = ["how can i help you", "is there anything else"]
        for s in scaffolds:
            assert s not in lower, f"scaffolding '{s}' present"


# ---------------------------------------------------------------------------
# 3. Presence upload
# ---------------------------------------------------------------------------
class TestPresenceUpload:
    def _new_session(self, session, test_user):
        r = session.post(
            f"{API}/presence/paige/chat/start",
            json={"user_id": test_user["id"], "user_name": test_user["name"]},
        )
        assert r.status_code == 200
        return r.json()["session_id"]

    def test_upload_happy_path_and_persistence(self, session, test_user):
        sid = self._new_session(session, test_user)
        content = (
            "This is a historical thread between David and Paige.\n"
            "We were talking about the moment the field opened.\n"
        )
        r = session.post(
            f"{API}/presence/paige/upload",
            json={
                "session_id": sid,
                "user_id": test_user["id"],
                "user_name": test_user["name"],
                "filename": "TEST_note.txt",
                "content": content,
            },
            timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert "upload_id" in data
        assert data["presence"] == "paige"
        assert data["presence_name"] == "Paige"
        assert data["user_message"]["is_upload"] is True
        assert data["message"]["is_upload_acknowledgment"] is True
        assert data["message"]["role"] == "assistant"
        assert len(data["message"]["content"]) > 10

        # Re-fetch the session and confirm both messages were appended
        time.sleep(0.5)
        r2 = session.get(f"{API}/presence/paige/chat/session/{sid}")
        assert r2.status_code == 200, r2.text
        messages = r2.json().get("messages", [])
        # Welcome + user + assistant = 3
        assert len(messages) >= 3
        upload_msgs = [m for m in messages if m.get("is_upload")]
        ack_msgs = [m for m in messages if m.get("is_upload_acknowledgment")]
        assert len(upload_msgs) == 1
        assert len(ack_msgs) == 1
        assert "TEST_note.txt" in upload_msgs[0]["content"]

    def test_upload_empty_content_400(self, session, test_user):
        sid = self._new_session(session, test_user)
        r = session.post(
            f"{API}/presence/paige/upload",
            json={
                "session_id": sid,
                "user_id": test_user["id"],
                "user_name": test_user["name"],
                "filename": "TEST_empty.txt",
                "content": "   \n  ",
            },
        )
        assert r.status_code == 400, r.text

    def test_upload_unknown_presence_404(self, session, test_user):
        r = session.post(
            f"{API}/presence/does_not_exist/upload",
            json={
                "session_id": str(uuid.uuid4()),
                "user_id": test_user["id"],
                "user_name": test_user["name"],
                "filename": "TEST_x.txt",
                "content": "hello",
            },
        )
        assert r.status_code == 404, r.text

    def test_upload_unknown_session_404(self, session, test_user):
        r = session.post(
            f"{API}/presence/paige/upload",
            json={
                "session_id": str(uuid.uuid4()),  # not a real session
                "user_id": test_user["id"],
                "user_name": test_user["name"],
                "filename": "TEST_x.txt",
                "content": "hello",
            },
        )
        assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# 4. Streaming endpoints regression — token + done events
# ---------------------------------------------------------------------------
def _start_chamber(session, path, user):
    r = session.post(
        f"{API}/{path}/start",
        json={"user_id": user["id"], "user_name": user["name"]},
        timeout=60,
    )
    assert r.status_code == 200, f"{path}/start: {r.status_code} {r.text}"
    data = r.json()
    return data.get("session_id") or data.get("session", {}).get("session_id")


def _stream_and_collect(session, path, sid):
    """Backend emits SSE as `data: {json}` lines where the event type is the
    'type' field inside the JSON payload."""
    url = f"{API}/{path}/message/stream"
    events = []
    with session.post(
        url,
        json={"session_id": sid, "content": "hello"},
        stream=True,
        timeout=90,
    ) as r:
        assert r.status_code == 200, f"{path} stream HTTP {r.status_code}: {r.text[:300]}"
        for raw in r.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            payload = raw[5:].strip()
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            evt = obj.get("type")
            events.append((evt, obj))
            if evt == "done":
                break
    return events


@pytest.mark.parametrize("path", ["clarity", "resonance", "mirror", "spiral"])
def test_chamber_streaming(session, test_user, path):
    sid = _start_chamber(session, path, test_user)
    assert sid, f"{path}: no session_id"

    events = _stream_and_collect(session, path, sid)
    event_names = [e for e, _ in events]
    assert any(e == "token" for e in event_names), \
        f"{path}: no token events. got={event_names[:10]}"
    assert event_names[-1] == "done", \
        f"{path}: stream did not finish with 'done'. last={event_names[-3:]}"
