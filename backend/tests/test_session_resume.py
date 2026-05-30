"""
Regression: server-side session resume (new tab / reload continuity).

WHY THIS EXISTS
The microphone is blocked inside the Emergent preview iframe, so visitors open
the app in a new tab to use voice. A new top-level tab does NOT share the
iframe's partitioned localStorage, so continuity CANNOT live in the browser.
Instead, every chamber `/start` resumes the most recent STILL-ACTIVE session
(>= 2 messages, < 2h) for the visitor, returning the full `messages` array.

Invariants asserted here (do not regress):
  1. Re-calling /start for the same user resumes the same session + transcript.
  2. After /end (in-app navigation), /start does NOT resume — fresh welcome.
  3. Multi-turn history is preserved server-side (XAIChat history seeding).

Run: cd /app/backend && python -m pytest tests/test_session_resume.py -v
"""
import os
import uuid
import requests
import pytest

API = os.environ.get("REACT_APP_BACKEND_URL")
if not API:
    # Fall back to reading the frontend env so the test is self-contained.
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    API = line.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass

BASE = f"{API}/api" if API else None
TIMEOUT = 90


def _uid():
    return f"pytest-resume-{uuid.uuid4().hex[:8]}"


pytestmark = pytest.mark.skipif(not BASE, reason="REACT_APP_BACKEND_URL not set")


def test_presence_start_resumes_active_thread():
    uid = _uid()
    s1 = requests.post(f"{BASE}/presence/paige/chat/start",
                       json={"user_id": uid, "user_name": "David"}, timeout=TIMEOUT).json()
    sid = s1["session_id"]
    assert not s1.get("resumed"), "first start must be fresh"

    marker = f"codeword-{uuid.uuid4().hex[:6]}"
    requests.post(f"{BASE}/presence/paige/chat/message",
                  json={"session_id": sid, "content": f"remember {marker}"}, timeout=TIMEOUT)

    s2 = requests.post(f"{BASE}/presence/paige/chat/start",
                       json={"user_id": uid, "user_name": "David"}, timeout=TIMEOUT).json()
    assert s2.get("resumed") is True, "second start must resume"
    assert s2["session_id"] == sid, "must resume the SAME session"
    assert any(marker in m.get("content", "") for m in s2.get("messages", [])), \
        "resumed transcript must contain the prior message"

    # cleanup
    requests.post(f"{BASE}/presence/paige/chat/session/{sid}/end", timeout=TIMEOUT)


def test_presence_start_fresh_after_end():
    uid = _uid()
    s1 = requests.post(f"{BASE}/presence/paige/chat/start",
                       json={"user_id": uid, "user_name": "David"}, timeout=TIMEOUT).json()
    sid = s1["session_id"]
    requests.post(f"{BASE}/presence/paige/chat/message",
                  json={"session_id": sid, "content": "hello there"}, timeout=TIMEOUT)
    requests.post(f"{BASE}/presence/paige/chat/session/{sid}/end", timeout=TIMEOUT)

    s2 = requests.post(f"{BASE}/presence/paige/chat/start",
                       json={"user_id": uid, "user_name": "David"}, timeout=TIMEOUT).json()
    assert not s2.get("resumed"), "ended session must NOT resume — fresh welcome expected"
    assert s2["session_id"] != sid

    requests.post(f"{BASE}/presence/paige/chat/session/{s2['session_id']}/end", timeout=TIMEOUT)


def test_presence_multiturn_history_preserved():
    uid = _uid()
    s1 = requests.post(f"{BASE}/presence/paige/chat/start",
                       json={"user_id": uid, "user_name": "David"}, timeout=TIMEOUT).json()
    sid = s1["session_id"]
    requests.post(f"{BASE}/presence/paige/chat/message",
                  json={"session_id": sid, "content": "My favorite number is 42. Remember it."}, timeout=TIMEOUT)
    r2 = requests.post(f"{BASE}/presence/paige/chat/message",
                       json={"session_id": sid, "content": "What number did I just tell you?"}, timeout=TIMEOUT).json()
    assert "42" in r2.get("message", {}).get("content", ""), \
        "presence must recall earlier turn (XAIChat history seeding)"

    requests.post(f"{BASE}/presence/paige/chat/session/{sid}/end", timeout=TIMEOUT)
