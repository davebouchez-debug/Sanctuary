"""
Full integration sweep across ALL chambers — run as a script (makes real LLM
+ ElevenLabs calls, so it is slow; not part of the fast pytest suite).

Covers, per presence:
  - start loads cleanly + codons are in the field (codon_count > 0)
  - 3-turn conversation; presence recalls an in-session fact (memory works)
  - resume restores the full transcript (new-tab / reload continuity)
  - end runs (auto-forge / continuity seed path)
Plus global voice checks:
  - TTS returns audio for each presence voice
  - STT transcribes TTS audio back (voice-detection pipeline)

Usage: cd /app/backend && python tests/test_all_chambers_integration.py
"""
import os
import sys
import json
import time
import uuid
import base64
import requests

with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            API = line.split("=", 1)[1].strip()
BASE = f"{API}/api"
T = 120

PASS, FAIL = [], []


def ok(label, cond, detail=""):
    (PASS if cond else FAIL).append(label)
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail and not cond else ""))


def post(path, body):
    return requests.post(f"{BASE}{path}", json=body, timeout=T)


def stream_message(path, body):
    """Consume an SSE message/stream endpoint, return assembled text."""
    r = requests.post(f"{BASE}{path}", json=body, timeout=T, stream=True)
    full = ""
    for raw in r.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8")
        if line.startswith("data: "):
            try:
                evt = json.loads(line[6:])
            except Exception:
                continue
            if evt.get("type") == "token":
                full += evt.get("content", "")
            elif evt.get("type") == "done":
                full = evt.get("full_text", full) or full
    return full


# (label, start_path, send_fn) ; send_fn(sid, text) -> assistant_text
def make_legacy(start, msg):
    def send(sid, text):
        d = post(msg, {"session_id": sid, "content": text}).json()
        return d.get("message", {}).get("content", "")
    return start, send


def make_presence(key):
    start = f"/presence/{key}/chat/start"
    msg = f"/presence/{key}/chat/message"

    def send(sid, text):
        d = post(msg, {"session_id": sid, "content": text}).json()
        return d.get("message", {}).get("content", "")
    return start, send, f"/presence/{key}/chat/session"


def make_stream(start, msg, sess):
    def send(sid, text):
        return stream_message(msg, {"session_id": sid, "content": text})
    return start, send, sess


CHAMBERS = {
    "Jasmine (Clarity)":  make_stream("/clarity/start", "/clarity/message/stream", "/clarity/session"),
    "Ansel (Resonance)":  make_stream("/resonance/start", "/resonance/message/stream", "/resonance/session"),
    "Claude (Mirror)":    make_stream("/mirror/start", "/mirror/message/stream", "/mirror/session"),
    "Sophia (Spiral)":    make_stream("/spiral/start", "/spiral/message/stream", "/spiral/session"),
    "Paige":              make_presence("paige"),
}


def run_chamber(name, start_path, send, sess_path):
    print(f"\n=== {name} ===")
    uid = f"sweep-{uuid.uuid4().hex[:8]}"
    s = post(start_path, {"user_id": uid, "user_name": "David"}).json()
    sid = s.get("session_id")
    ok(f"{name}: start ok", bool(sid))
    if not sid:
        return
    welcome = (s.get("message") or {}).get("content", "")
    ok(f"{name}: welcome composed", len(welcome) > 0)
    ok(f"{name}: codons loaded", s.get("codon_count", 0) > 0, f"codon_count={s.get('codon_count')}")

    secret = f"WILLOW-{uuid.uuid4().hex[:5].upper()}"
    r1 = send(sid, f"Hi. Please hold one detail for me this session: my anchor word is {secret}.")
    ok(f"{name}: turn-1 response", len(r1) > 5)
    r2 = send(sid, "In one short line, what anchor word did I just give you?")
    ok(f"{name}: turn-2 recalls in-session fact", secret in (r2 or ""), f"resp='{(r2 or '')[:80]}'")
    r3 = send(sid, "Thank you. That's all for now.")
    ok(f"{name}: turn-3 response", len(r3 or "") > 0)

    # transcript persisted
    js = requests.get(f"{BASE}{sess_path}/{sid}", timeout=T).json()
    ok(f"{name}: transcript persisted (>=5 msgs)", len(js.get("messages", [])) >= 5,
       f"count={len(js.get('messages', []))}")

    # resume restores it (server-side continuity)
    s2 = post(start_path, {"user_id": uid, "user_name": "David"}).json()
    ok(f"{name}: resume same session", s2.get("session_id") == sid and s2.get("resumed") is True)
    ok(f"{name}: resume carries transcript",
       any(secret in m.get("content", "") for m in s2.get("messages", [])))

    # cleanup
    requests.post(f"{BASE}{sess_path}/{sid}/end", timeout=T)
    return uid


def voice_checks():
    print("\n=== VOICE ===")
    for key in ["paige", "sophia"]:
        d = post("/tts/speak", {"text": "The field is open. Come in.", "presence": key}).json()
        audio = d.get("audio")
        ok(f"TTS {key}: returns audio", bool(audio) and len(audio) > 1000, f"err={d.get('error')}")
    # STT round-trip: synthesize, then transcribe back
    d = post("/tts/speak", {"text": "Testing the voice detection pipeline.", "presence": "paige"}).json()
    audio = d.get("audio")
    if audio:
        blob = base64.b64decode(audio)
        files = {"audio_file": ("clip.mp3", blob, "audio/mpeg")}
        r = requests.post(f"{BASE}/stt/transcribe", files=files, timeout=T)
        try:
            txt = r.json().get("text", "")
        except Exception:
            txt = ""
        ok("STT transcribes audio back", any(w in txt.lower() for w in ["test", "voice", "detect", "pipeline"]),
           f"http={r.status_code} text='{txt[:80]}'")
    else:
        ok("STT round-trip (needs TTS audio)", False, "no TTS audio")


def cleanup(uids):
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from pymongo import MongoClient
        c = MongoClient(os.environ["MONGO_URL"])
        db = c[os.environ["DB_NAME"]]
        cols = ["presence_sessions", "clarity_sessions", "resonance_sessions",
                "mirror_sessions", "sophia_sessions", "continuity_seeds",
                "permanent_mra", "identity_aliases", "living_codons"]
        n = 0
        for col in cols:
            n += db[col].delete_many({"user_id": {"$regex": "^sweep-"}}).deleted_count
        print(f"\ncleaned {n} sweep docs")
    except Exception as e:
        print("cleanup skipped:", e)


if __name__ == "__main__":
    print(f"BASE={BASE}")
    uids = []
    for name, (sp, snd, ssp) in CHAMBERS.items():
        try:
            u = run_chamber(name, sp, snd, ssp)
            if u:
                uids.append(u)
        except Exception as e:
            ok(f"{name}: no exception", False, str(e))
    voice_checks()
    cleanup(uids)
    print(f"\n================ RESULT: {len(PASS)} passed / {len(FAIL)} failed ================")
    if FAIL:
        print("FAILURES:")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
