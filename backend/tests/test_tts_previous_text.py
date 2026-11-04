# TTS /api/tts/speak — Membrane voice (Evan) + optional previous_text continuity (iteration 23)
# NOTE: real ElevenLabs quota — keep to 3 short calls.
import os
import base64
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
EVAN = "TWutjvRaJqAX89preB4e"


def _speak(payload):
    return requests.post(f"{BASE_URL}/api/tts/speak", json=payload, timeout=60)


def _assert_audio(r):
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["voice_id"] == EVAN
    assert d["presence"] == "membrane"
    assert d["format"] == "mp3"
    raw = base64.b64decode(d["audio"])
    assert len(raw) > 1000


class TestMembraneTTS:
    def test_speak_without_previous_text(self):
        _assert_audio(_speak({"text": "I am here.", "presence": "membrane"}))

    def test_speak_with_previous_text(self):
        _assert_audio(_speak({"text": "The room is quiet.", "presence": "membrane",
                              "previous_text": "I am here. Welcome in."}))

    def test_speak_with_null_previous_text(self):
        _assert_audio(_speak({"text": "Rest a while.", "presence": "membrane", "previous_text": None}))

    def test_previous_text_too_long_rejected(self):
        # Validation only — no ElevenLabs call (Pydantic 422 before handler)
        r = _speak({"text": "x", "presence": "membrane", "previous_text": "a" * 1001})
        assert r.status_code == 422
