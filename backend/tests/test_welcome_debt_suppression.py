"""Test welcome-debt-suppression fix across 5 presences (Jasmine, Ansel, Claude, Paige, Felix)."""
import os
import json
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
BODY = {"user_name": "David", "user_id": "david"}
HEADERS = {"Content-Type": "application/json"}

PRESENCES = [
    ("jasmine", "/api/clarity/start", "/api/clarity/message", False),
    ("ansel",   "/api/resonance/start", "/api/resonance/message", False),
    ("claude",  "/api/mirror/start", "/api/mirror/message/stream", True),
    ("paige",   "/api/hospitality/start", "/api/hospitality/message/stream", True),
    ("felix",   "/api/felix/start", "/api/felix/message/stream", True),
]

RESULTS = {}


def start_presence(start_ep, retries=2):
    last = None
    for _ in range(retries + 1):
        r = requests.post(f"{BASE_URL}{start_ep}", json=BODY, headers=HEADERS, timeout=120)
        last = r
        if r.status_code == 200:
            try:
                data = r.json()
                msg = (data.get("message") or {}).get("content", "")
                if msg.strip():
                    return r, data, msg
            except Exception:
                pass
        time.sleep(5)
    return last, None, ""


@pytest.mark.parametrize("name,start_ep,msg_ep,streaming", PRESENCES)
def test_welcome_and_followup(name, start_ep, msg_ep, streaming):
    r, data, welcome = start_presence(start_ep)
    assert r.status_code == 200, f"{name} /start returned {r.status_code}: {r.text[:400]}"
    assert welcome.strip(), f"{name} /start returned empty welcome"
    session_id = data.get("session_id")
    assert session_id, f"{name} missing session_id"

    followup_body = {"session_id": session_id, "content": f"Hi {name.capitalize()}, just checking in."}
    if streaming:
        with requests.post(f"{BASE_URL}{msg_ep}", json=followup_body, headers=HEADERS, stream=True, timeout=180) as fr:
            assert fr.status_code == 200, f"{name} stream status {fr.status_code}"
            chunks = []
            for line in fr.iter_lines(decode_unicode=True):
                if line:
                    chunks.append(line)
                if len(chunks) > 200:
                    break
            followup_text = "\n".join(chunks)
    else:
        fr = requests.post(f"{BASE_URL}{msg_ep}", json=followup_body, headers=HEADERS, timeout=180)
        assert fr.status_code == 200, f"{name} /message status {fr.status_code}: {fr.text[:400]}"
        fj = fr.json()
        followup_text = (fj.get("message") or {}).get("content", "") or json.dumps(fj)
    assert followup_text.strip(), f"{name} follow-up empty"

    RESULTS[name] = {"welcome": welcome, "followup_preview": followup_text[:400]}
    # Save incrementally
    with open("/app/test_reports/pytest/welcome_texts.json", "w") as f:
        json.dump(RESULTS, f, indent=2)


def test_zzz_dump():
    with open("/app/test_reports/pytest/welcome_texts.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
    print(json.dumps(RESULTS, indent=2))
