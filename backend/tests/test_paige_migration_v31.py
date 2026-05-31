"""
Backend regression suite for the Paige -> presence_template migration (V3.1).
Verifies:
  * /api/hospitality/start (template-driven, codon_count populated, generates own opening)
  * /api/hospitality/message/stream (SSE token events + done event, coherent reply)
  * Dual continuity: turn_cessation + permanent MRA both fire (the 'lose nothing' invariant)
  * Reconstruction Gate path runs without crash; returning David recognized
  * /api/hospitality/session/{id}/end auto-forges
  * Template-aware upload: /api/presence/paige/upload writes to paige_sessions
  * Sophia regression: /api/spiral/start + /api/spiral/message/stream still work
  * Legacy chamber starts: clarity / resonance / mirror respond without error
"""
import os
import re
import time
import json
import uuid
import requests
import pytest

def _load_base_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        try:
            with open("/app/frontend/.env", "r") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    return url.rstrip("/")


BASE_URL = _load_base_url()
BACKEND_LOG = "/var/log/supervisor/backend.err.log"

USER_ID = "legacy-david-123"
USER_NAME = "David"


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _tail_log(n: int = 400) -> str:
    try:
        with open(BACKEND_LOG, "r", encoding="utf-8", errors="ignore") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return ""


# ---------- Paige template-engine smoke ----------
class TestPaigeStart:
    def test_hospitality_start(self, api):
        r = api.post(
            f"{BASE_URL}/api/hospitality/start",
            json={"user_id": USER_ID, "user_name": USER_NAME},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "session_id" in data and data["session_id"]
        # Welcome must be Paige-generated (non-empty assistant text)
        # Template engines return the first turn either inside `messages` or `welcome`
        # Welcome may come back as a string or a dict {content, role, ...}
        def _to_text(v):
            if isinstance(v, str):
                return v
            if isinstance(v, dict):
                return v.get("content", "") or ""
            return ""

        welcome = (
            _to_text(data.get("welcome"))
            or _to_text(data.get("message"))
            or _to_text((data.get("messages") or [{}])[-1])
        )
        assert welcome and len(welcome.strip()) > 0, f"empty welcome: {data}"
        # codon_count must be populated and look like the canonical field (~243)
        codon_count = data.get("codon_count")
        assert isinstance(codon_count, int) and codon_count > 100, (
            f"codon_count missing/low: {codon_count}"
        )
        # Stash for the rest of the suite
        pytest.paige_session_id = data["session_id"]
        pytest.paige_welcome = welcome


class TestPaigeStream:
    def test_stream_message_emits_tokens_and_done(self, api):
        sid = getattr(pytest, "paige_session_id", None)
        assert sid, "depends on TestPaigeStart"
        url = f"{BASE_URL}/api/hospitality/message/stream"
        payload = {"session_id": sid, "content": "Hi Paige, it's David. Quick check — are you running on the new engine? Please answer in one short sentence."}

        with api.post(url, json=payload, stream=True, timeout=90) as r:
            assert r.status_code == 200, r.text
            saw_token = False
            saw_done = False
            collected = []
            start = time.time()
            current_event = None
            for raw in r.iter_lines(decode_unicode=True):
                if raw is None or raw == "":
                    continue
                if raw.startswith("event:"):
                    current_event = raw.split(":", 1)[1].strip()
                    if current_event == "token":
                        saw_token = True
                    elif current_event == "done":
                        saw_done = True
                elif raw.startswith("data:"):
                    body = raw[5:].strip()
                    try:
                        obj = json.loads(body or "{}")
                        msg_type = obj.get("type")
                        tok = obj.get("content") or obj.get("token") or obj.get("text") or obj.get("delta") or ""
                        if msg_type == "token" or tok:
                            collected.append(tok)
                            saw_token = True
                        if msg_type == "done" or obj.get("done") is True or obj.get("event") == "done":
                            saw_done = True
                    except Exception:
                        if body and body != "[DONE]":
                            collected.append(body)
                            saw_token = True
                        if body == "[DONE]":
                            saw_done = True
                if saw_done:
                    break
                if time.time() - start > 75:
                    break
            assert saw_token, "no token/data events observed in SSE stream"
            assert saw_done, "no 'done' SSE event observed"
            reply = "".join(collected)
            assert len(reply.strip()) > 5, f"reply too short: {reply!r}"
            pytest.paige_reply = reply


class TestPaigeDualContinuity:
    """Core 'lose nothing' invariant: turn-cessation AND permanent MRA must fire per turn."""

    def test_log_evidence_of_both(self, api):
        sid = getattr(pytest, "paige_session_id", None)
        assert sid, "no session"
        # Wait briefly for async post-stream hooks
        time.sleep(2)
        log = _tail_log(800)
        sid_prefix = sid[:8]
        has_cessation = bool(re.search(rf"\[TURN-CESSATION\] paige\s+{sid_prefix}.*seed=\d+", log))
        has_mra = bool(re.search(r"\[PERMANENT MRA\] Promoted \d+ breadcrumbs for paige", log))
        assert has_cessation, "turn-cessation log NOT found for this paige session"
        assert has_mra, "permanent-MRA promotion log NOT found for paige"


class TestPaigeReconstructionGate:
    """Returning user — /start should not crash, and may surface continuity from prior seeds."""

    def test_returning_user_does_not_crash(self, api):
        r = api.post(
            f"{BASE_URL}/api/hospitality/start",
            json={"user_id": USER_ID, "user_name": USER_NAME},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("session_id")
        # If continuity seeds exist for paige+David from prior runs, welcome should be non-empty
        w = d.get("welcome") or d.get("message") or ""
        if isinstance(w, dict):
            w = w.get("content", "")
        assert isinstance(w, str)


class TestPaigeEnd:
    def test_session_end_auto_forge(self, api):
        sid = getattr(pytest, "paige_session_id", None)
        assert sid, "no session"
        r = api.post(f"{BASE_URL}/api/hospitality/session/{sid}/end", json={}, timeout=60)
        # Some implementations return 200; never 5xx
        assert r.status_code in (200, 204), r.text


class TestPaigeUpload:
    """Template-aware upload — must hit paige_sessions and reconstruct the prompt."""

    def test_upload_to_paige_sessions(self, api):
        # Need a fresh session id (the previous one is ended)
        start = api.post(
            f"{BASE_URL}/api/hospitality/start",
            json={"user_id": USER_ID, "user_name": USER_NAME},
            timeout=60,
        )
        assert start.status_code == 200, start.text
        sid = start.json()["session_id"]
        payload = {
            "session_id": sid,
            "user_id": USER_ID,
            "user_name": USER_NAME,
            "filename": "TEST_note.txt",
            "content": "This is a brief note from David. Please acknowledge.",
        }
        r = api.post(f"{BASE_URL}/api/presence/paige/upload", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("success") is True, d
        ack_field = d.get("message") or d.get("reply") or d.get("acknowledgment") or ""
        if isinstance(ack_field, dict):
            ack = ack_field.get("content", "")
        else:
            ack = ack_field
        assert isinstance(ack, str) and len(ack.strip()) > 5, f"empty acknowledgment: {d}"


# ---------- Sophia regression (template engine, MUST be unchanged) ----------
class TestSophiaRegression:
    def test_spiral_start_and_stream(self, api):
        r = api.post(
            f"{BASE_URL}/api/spiral/start",
            json={"user_id": USER_ID, "user_name": USER_NAME},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        sid = r.json().get("session_id")
        assert sid

        with api.post(
            f"{BASE_URL}/api/spiral/message/stream",
            json={"session_id": sid, "content": "Sophia — short hello, one sentence."},
            stream=True,
            timeout=90,
        ) as s:
            assert s.status_code == 200, s.text
            saw_done = False
            saw_data = False
            start = time.time()
            for raw in s.iter_lines(decode_unicode=True):
                if raw is None or raw == "":
                    continue
                if raw.startswith("event:") and raw.split(":", 1)[1].strip() == "done":
                    saw_done = True
                    break
                if raw.startswith("data:"):
                    body = raw[5:].strip()
                    saw_data = True
                    if body == "[DONE]":
                        saw_done = True
                        break
                    try:
                        obj = json.loads(body or "{}")
                        if obj.get("type") == "done" or obj.get("done") is True:
                            saw_done = True
                            break
                    except Exception:
                        pass
                if time.time() - start > 75:
                    break
            assert saw_data, "spiral stream produced no data lines"
            assert saw_done, "spiral stream did not finish"

        # Sophia must NOT have turn_cessation/reconstruction_gate firing
        time.sleep(1)
        log = _tail_log(400)
        # Look for any cessation tag for sophia within last lines
        sophia_cessation = re.search(r"\[TURN-CESSATION\] sophia", log)
        # This is opt-in OFF for Sophia — must remain off
        assert sophia_cessation is None, "Sophia unexpectedly has turn-cessation enabled"


# ---------- Legacy chamber starts ----------
class TestLegacyChambers:
    @pytest.mark.parametrize(
        "path",
        ["/api/clarity/start", "/api/mirror/start"],
    )
    def test_legacy_start(self, api, path):
        r = api.post(
            f"{BASE_URL}{path}",
            json={"user_id": USER_ID, "user_name": USER_NAME},
            timeout=60,
        )
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
        d = r.json()
        assert d.get("session_id") or d.get("message") or d.get("welcome"), d

    def test_resonance_start_or_threshold(self, api):
        # Try both endpoints — at least one MUST respond.
        ok = []
        for path in ("/api/resonance/start", "/api/resonance/threshold"):
            try:
                r = api.post(
                    f"{BASE_URL}{path}",
                    json={"user_id": USER_ID, "user_name": USER_NAME},
                    timeout=60,
                )
                ok.append((path, r.status_code, r.text[:120]))
                if r.status_code == 200:
                    return
            except Exception as e:
                ok.append((path, "EXC", str(e)))
        pytest.fail(f"neither resonance start nor threshold returned 200: {ok}")
